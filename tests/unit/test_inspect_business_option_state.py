from tools.inspect_business_option_state import payload_summary


class Request:
    post_data = (
        '--boundary\r\nContent-Disposition: form-data; name="CityName"\r\n\r\nСамара\r\n'
        '--boundary\r\nContent-Disposition: form-data; name="City"\r\n\r\n36401\r\n'
        '--boundary\r\nContent-Disposition: form-data; name="Place"\r\n\r\nДля бизнеса\r\n'
        '--boundary\r\nContent-Disposition: form-data; name="Phone"\r\n\r\n9999999999\r\n--boundary--'
    )


def test_payload_summary_keeps_samara_business_values_and_masks_phone():
    summary = payload_summary(Request())
    assert summary["selected_values"] == {"CityName": "Самара", "City": "36401", "Place": "Для бизнеса"}
    assert "Phone" in summary["field_names"]
    assert "9999999999" not in repr(summary)
