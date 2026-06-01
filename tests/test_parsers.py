from __future__ import annotations

import json
from urllib.parse import unquote_plus

import pytest

from xiaobiu import SuningSmartHomeClient, parse_jsonp_or_json
from xiaobiu.client import (
  AuthenticationError,
  CaptchaRequiredError,
  CaptchaSolution,
  DEVICE_LIST_URL,
  FAMILY_LIST_URL,
  MOBILE_SMS_LOGIN_APP_CODE,
  MOBILE_SMS_LOGIN_CHANNEL,
  MOBILE_SMS_LOGIN_ORDER_CHANNEL,
  MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE,
  MOBILE_SMS_LOGIN_SCENE_ID,
  SignedRequestTemplate,
  SmsRateLimitedError,
  _air_conditioner_status_payload,
  _build_gs_sign,
  _build_parser,
  _captcha_kind_from_risk_type,
  _send_sms_with_optional_prompt,
  extract_risk_context_script_urls,
  main as client_main,
  parse_login_page_config,
)
from xiaobiu.crypto import SuAESCipher
from xiaobiu.models import CaptchaBridgeResult

SAMPLE_LOGIN_PAGE = """
<script>
var loginPBK="LOGIN_PBK";
var rdsyKey="RDSY_KEY";
var ssojbossConstant = {
  rdsyAppCode:"APP_CODE",
  stepFlag:"STEP_ONE",
  stepTwoFlag:"STEP_TWO",
  rdsySceneId:"PASSPORT",
  rdsySceneIdYGHK:"PASSPORT_YGHK",
  stepThreeFlag:"STEP_THREE",
  channel:"PC",
  checkAccountKey: "CHECK_ACCOUNT_KEY"
};
</script>
"""


def test_parse_login_page_config() -> None:
  config = parse_login_page_config(SAMPLE_LOGIN_PAGE)
  assert config.rdsy_app_code == "APP_CODE"
  assert config.step_two_flag == "STEP_TWO"
  assert config.check_account_key == "CHECK_ACCOUNT_KEY"




def test_extract_risk_context_script_urls() -> None:
  html_text = """
  <script src="https://mmds.suning.com/mmds/mmds.js?appCode=qEmt9X4YmoV2Vye8"></script>
  <script src="https://oss.suning.com/mmds/mmds/js/hash/mmds.bundle.js"></script>
  <script src="https://dfp.suning.com/dfprs-collect/dist/fp.js?appCode=qEmt9X4YmoV2Vye8"></script>
  """

  assert extract_risk_context_script_urls(html_text) == [
    "https://mmds.suning.com/mmds/mmds.js?appCode=qEmt9X4YmoV2Vye8",
    "https://oss.suning.com/mmds/mmds/js/hash/mmds.bundle.js",
    "https://dfp.suning.com/dfprs-collect/dist/fp.js?appCode=qEmt9X4YmoV2Vye8",
  ]




def test_parse_jsonp_or_json_supports_both_formats() -> None:
  assert parse_jsonp_or_json('{"code":"0"}') == {"code": "0"}
  assert parse_jsonp_or_json('smsLogin({"code":"0"})') == {"code": "0"}


