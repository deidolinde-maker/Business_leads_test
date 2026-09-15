"""Fail-closed, one-shot POST dispatch. Never rewrites a lead's city or payload."""
import json
from email import policy
from email.parser import BytesParser
from urllib.parse import parse_qs, urlsplit

from business.errors import BusinessCheckError, ConfigurationError


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BusinessCheckError("duplicate_json_field")
        result[key] = value
    return result


def parse_payload(content_type: str, body: bytes) -> dict:
    media = content_type.partition(";")[0].strip().lower()
    if media == "application/json":
        parsed = json.loads(body, object_pairs_hook=_unique_object)
        if not isinstance(parsed, dict):
            raise BusinessCheckError("payload_must_be_object")
        return parsed
    if media == "application/x-www-form-urlencoded":
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
        return {key: values[0] if len(values) == 1 else values for key, values in parsed.items()}
    if media == "multipart/form-data":
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
        )
        if not message.is_multipart():
            raise BusinessCheckError("invalid_multipart")
        result = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name or part.get_filename() is not None:
                raise BusinessCheckError("unsupported_multipart_part")
            if name in result:
                raise BusinessCheckError("duplicate_multipart_field")
            result[name] = part.get_content()
        return result
    raise BusinessCheckError("unsupported_payload_encoding")


def lookup(payload: dict, path: str):
    value = payload
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise BusinessCheckError(f"missing_contract_field:{path}")
        value = value[key]
    return value


def matches(payload: dict, expected: dict, label: str):
    for path, value in expected.items():
        actual = lookup(payload, path)
        # bool True must not equal city ID 1; retain exact JSON/form types.
        if type(actual) is not type(value) or actual != value:
            raise BusinessCheckError(f"{label}_mismatch:{path}")


def validate_contract(contract: dict):
    endpoint = urlsplit(contract.get("url", ""))
    if endpoint.scheme not in {"http", "https"} or not endpoint.hostname or endpoint.username:
        raise ConfigurationError("verified submission URL required")
    if contract.get("method") != "POST":
        raise ConfigurationError("bootstrap supports verified POST contracts only")
    for key in ("region_match", "business_match", "identity_match"):
        if not isinstance(contract.get(key), dict) or not contract[key]:
            raise ConfigurationError(f"verified {key} required")
    if not contract.get("evidence"):
        raise ConfigurationError("submission contract needs evidence")
    if contract.get("target_city") != "Самара" or contract.get("target_city_ui_id") != "36401":
        raise ConfigurationError("contract must explicitly map its region_match to Samara / 36401")
    reply = contract.get("response", {})
    statuses = reply.get("statuses")
    if not statuses or any(type(s) is not int or s < 200 or s >= 400 or s in {307, 308} for s in statuses):
        raise ConfigurationError("explicit positive response statuses required; 307/308 unsupported")
    if not reply.get("json_match") and not reply.get("location"):
        raise ConfigurationError("response needs exact JSON or Location contract")
    for rule in contract.get("read_only_requests", []):
        if not rule.get("evidence") or not rule.get("url") or rule.get("method") not in {"POST", "GET"}:
            raise ConfigurationError("read-only exceptions need exact URL/method/evidence")
        if rule["url"] == contract["url"]:
            raise ConfigurationError("submission cannot be allowlisted as read-only")


class SubmissionGuard:
    def __init__(self, contract: dict, deadline):
        validate_contract(contract)
        self.contract = contract
        self.deadline = deadline
        self.armed = False
        self.seen = 0
        self.forwarded = 0
        self.accepted = False
        self.error = None
        self.evidence = {}
        self.handler = self._handle

    def install(self, context):
        context.route("**/*", self.handler)
        # This initial implementation deliberately has no WebSocket lead adapter.
        context.route_web_socket("**/*", lambda ws: ws.close())

    def arm(self):
        if self.armed or self.seen:
            raise BusinessCheckError("submit_already_attempted")
        self.armed = True

    def _abort(self, route, reason):
        self.error = self.error or reason
        route.abort("blockedbyclient")

    def _handle(self, route):
        request = route.request
        target = self.contract["url"]
        # Changed query strings on the same endpoint are not a reason to bypass validation.
        current = urlsplit(request.url)
        expected = urlsplit(target)
        same_endpoint = (current.scheme, current.netloc, current.path) == (expected.scheme, expected.netloc, expected.path)
        if same_endpoint:
            self.seen += 1
            if not self.armed:
                return self._abort(route, "submission_before_explicit_click")
            if self.seen > 1:
                return self._abort(route, "duplicate_submission")
            if request.method != self.contract["method"] or request.url != target:
                return self._abort(route, "submission_endpoint_changed")
            try:
                payload = parse_payload(request.headers.get("content-type", ""), request.post_data_buffer or b"")
                matches(payload, self.contract["region_match"], "region")
                matches(payload, self.contract["business_match"], "business")
                matches(payload, self.contract["identity_match"], "identity")
                self.evidence = {
                    "url": target, "method": request.method, "region_checked": True,
                    "business_checked": True, "identity_checked": True,
                }
                # Dispatch this exact request only after validation. Never retry or auto-follow a redirecting POST.
                self.forwarded += 1
                response = route.fetch(max_redirects=0, max_retries=0, timeout=self.deadline.ms())
                self.evidence["status"] = response.status
                reply = self.contract["response"]
                if response.status not in reply["statuses"]:
                    raise BusinessCheckError("submission_response_rejected")
                if reply.get("json_match"):
                    matches(response.json(), reply["json_match"], "response")
                if reply.get("location") and response.headers.get("location") != reply["location"]:
                    raise BusinessCheckError("response_location_mismatch")
                self.accepted = True
                route.fulfill(response=response)
            except Exception as exc:
                # Do not expose payload or potentially sensitive exception text.
                reason = str(exc) if isinstance(exc, BusinessCheckError) else f"submission_unconfirmed:{type(exc).__name__}"
                self._abort(route, reason)
            return
        for rule in self.contract.get("read_only_requests", []):
            if request.url == rule["url"] and request.method == rule["method"]:
                if request.method == "POST":
                    try:
                        response = route.fetch(max_redirects=0, max_retries=0, timeout=self.deadline.ms())
                        if 300 <= response.status < 400:
                            return self._abort(route, "read_only_post_redirect_not_supported")
                        route.fulfill(response=response)
                    except Exception:
                        self._abort(route, "read_only_dependency_failed")
                else:
                    route.continue_()
                return
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            route.continue_()
        elif self.armed:
            self._abort(route, "unexpected_write_endpoint")
        else:
            # POST dependencies must be individually identified as read-only during onboarding.
            route.abort("blockedbyclient")

    def assert_success(self):
        if self.error:
            raise BusinessCheckError(self.error)
        if self.seen != 1 or self.forwarded != 1 or not self.accepted:
            raise BusinessCheckError("submission_not_confirmed")
