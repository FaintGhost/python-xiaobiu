# python-xiaobiu

Python client for Suning smart home SMS login and session management.

Used by the [ha-suning](https://github.com/FaintGhost/ha-suning) Home Assistant custom integration.

## Install

```bash
pip install python-xiaobiu
```

## Usage

```python
from xiaobiu import CaptchaRequiredError, SuningSmartHomeClient

client = SuningSmartHomeClient(state_path=".suning-session.json")

try:
    client.send_sms_code("13800000000")
except CaptchaRequiredError as error:
    print(error.risk_type, error.sms_ticket)

client.login_with_sms_code(phone_number="13800000000", sms_code="123456")
print(client.list_family_infos())
```

## CLI

```bash
# Interactive login
xiaobiucli login --phone 13800000000 --state-file .suning-session.json

# Send SMS only
xiaobiucli send-sms --phone 13800000000 --state-file .suning-session.json

# Check session
xiaobiucli check --state-file .suning-session.json

# List families / devices
xiaobiucli families --state-file .suning-session.json
xiaobiucli devices --family-id 37790 --state-file .suning-session.json
```

## Requirements

- Python >= 3.14
- `cryptography`, `pydantic`, `requests`
