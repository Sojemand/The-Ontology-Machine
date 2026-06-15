export const TARGET_ORDER = ["llm_shared", "embeddings"];
export const CREDENTIALS_STATE_FILE = "credentials_state.json";
export const OAUTH_TOKEN_FILE = "oauth_token.enc";
export const OAUTH_TOKEN_LOCK_FILE = "oauth_token.lock";
export const OAUTH_REPORT_FILE = "oauth_latest_report.json";
export const OAUTH_REFRESH_SKEW_SECONDS = 300;
export const PENDING_LOGIN_TTL_MS = 5 * 60 * 1000;

export const DEFAULT_OAUTH_SESSION = {
  status: "logged_out",
  account_label: "",
  status_message: "",
  client_id_hint: "",
  scope: "",
  expires_at: "",
  account_id: "",
  has_refresh_token: false
};

export const DEFAULT_CREDENTIALS_STATE = {
  targets: {
    llm_shared: { has_secret: false },
    embeddings: { has_secret: false }
  },
  oauth_session: { ...DEFAULT_OAUTH_SESSION }
};
