export const CONFIG_FILE_NAME = "config.json";
export const DEFAULT_DEMO_DB_RELATIVE_PATH = "SampleDB\\Consciousness Travel - Default Demo\\Corpus\\corpus.db";
export const DEFAULT_SQL_DATABASE_PATH = `..\\${DEFAULT_DEMO_DB_RELATIVE_PATH}`;

export const DEFAULT_CONFIG = {
  customer_name: "Vision Pipeline Case Worker",
  sql_database_path: DEFAULT_SQL_DATABASE_PATH,
  pipeline_root: "",
  llm_provider: "openai",
  llm_base_url: "https://api.openai.com/v1",
  llm_model: "gpt-5.4",
  llm_api_key: "",
  embedding_provider: "openai",
  embedding_base_url: "https://api.openai.com/v1",
  embedding_model: "text-embedding-3-small",
  embedding_api_key: "",
  port: 3000,
  theme: "dark",
  admin_secret: "",
  context_limit: 127096
};

export const EDITABLE_CONFIG_FIELDS = [
  "customer_name",
  "sql_database_path",
  "pipeline_root",
  "llm_provider",
  "llm_base_url",
  "llm_model",
  "embedding_provider",
  "embedding_base_url",
  "embedding_model",
  "port",
  "theme",
  "context_limit"
];

export const SECRET_FIELDS = ["llm_api_key", "embedding_api_key", "admin_secret"];

export const STORED_CONFIG_FIELDS = [...EDITABLE_CONFIG_FIELDS, ...SECRET_FIELDS];
