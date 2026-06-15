import { DEFAULT_CONFIG, EDITABLE_CONFIG_FIELDS, SECRET_FIELDS, STORED_CONFIG_FIELDS } from "./types.js";
import { normalizeStoredSqlDatabasePath } from "./database_path.js";
import { isPlainObject } from "./validation.js";
import { normalizeProviderId } from "../shared/provider_catalog.js";

const LEGACY_DEFAULT_CONTEXT_LIMIT = 128000;

function normalizeLoadedProvider(value, fallbackProvider = DEFAULT_CONFIG.llm_provider) {
  if (typeof value !== "string") {
    return fallbackProvider;
  }
  return normalizeProviderId(value, fallbackProvider);
}

function normalizeSavedProvider(value, currentConfig, field, source, fallbackProvider = DEFAULT_CONFIG.llm_provider) {
  if (!hasOwnField(source, field) || typeof value !== "string") {
    return normalizeLoadedProvider(currentConfig?.[field], fallbackProvider);
  }
  return normalizeProviderId(value, fallbackProvider);
}

function normalizeTheme(value) {
  return value === "light" ? "light" : "dark";
}

function normalizePort(value) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 1024 && parsed <= 65535 ? parsed : DEFAULT_CONFIG.port;
}

function normalizeContextLimit(value) {
  const parsed = Number(value);
  if (parsed === LEGACY_DEFAULT_CONTEXT_LIMIT) {
    return DEFAULT_CONFIG.context_limit;
  }
  return Number.isInteger(parsed) && parsed >= 4096 && parsed <= 2_000_000 ? parsed : DEFAULT_CONFIG.context_limit;
}

function cleanLoadedString(value, fallback) {
  if (typeof value !== "string") {
    return fallback;
  }
  const nextValue = value.trim();
  return nextValue || fallback;
}

function cleanIncomingString(value, fallback) {
  const nextValue = String(value ?? "").trim();
  return nextValue || fallback;
}

function normalizeLoadedSecret(value) {
  return typeof value === "string" ? value : "";
}

function hasOwnField(source, field) {
  return Boolean(source) && Object.prototype.hasOwnProperty.call(source, field);
}

const FIELD_POLICY = {
  customer_name: {
    load(value) {
      return cleanLoadedString(value, DEFAULT_CONFIG.customer_name);
    },
    save(value, currentConfig) {
      return cleanIncomingString(value, currentConfig.customer_name || DEFAULT_CONFIG.customer_name);
    }
  },
  sql_database_path: {
    load(value) {
      return typeof value === "string" ? normalizeStoredSqlDatabasePath(value) : DEFAULT_CONFIG.sql_database_path;
    },
    save(value, _currentConfig, field, source) {
      if (!hasOwnField(source, field)) {
        return normalizeStoredSqlDatabasePath(_currentConfig?.sql_database_path);
      }
      return normalizeStoredSqlDatabasePath(value);
    }
  },
  pipeline_root: {
    load(value) {
      return typeof value === "string" ? value.trim() : "";
    },
    save(value, currentConfig, field, source) {
      if (!hasOwnField(source, field)) {
        return String(currentConfig?.pipeline_root ?? "").trim();
      }
      return String(value ?? "").trim();
    }
  },
  llm_provider: {
    load(value) {
      return normalizeLoadedProvider(value, DEFAULT_CONFIG.llm_provider);
    },
    save(value, currentConfig, field, source) {
      return normalizeSavedProvider(value, currentConfig, field, source, DEFAULT_CONFIG.llm_provider);
    }
  },
  llm_base_url: {
    load(value) {
      return cleanLoadedString(value, DEFAULT_CONFIG.llm_base_url);
    },
    save(value, currentConfig) {
      return cleanIncomingString(value, currentConfig.llm_base_url || DEFAULT_CONFIG.llm_base_url);
    }
  },
  llm_model: {
    load(value) {
      return cleanLoadedString(value, DEFAULT_CONFIG.llm_model);
    },
    save(value, currentConfig) {
      return cleanIncomingString(value, currentConfig.llm_model || DEFAULT_CONFIG.llm_model);
    }
  },
  llm_api_key: { load: normalizeLoadedSecret },
  embedding_provider: {
    load(value) {
      return normalizeLoadedProvider(value, DEFAULT_CONFIG.embedding_provider);
    },
    save(value, currentConfig, field, source) {
      return normalizeSavedProvider(value, currentConfig, field, source, DEFAULT_CONFIG.embedding_provider);
    }
  },
  embedding_base_url: {
    load(value) {
      return cleanLoadedString(value, DEFAULT_CONFIG.embedding_base_url);
    },
    save(value, currentConfig) {
      return cleanIncomingString(value, currentConfig.embedding_base_url || DEFAULT_CONFIG.embedding_base_url);
    }
  },
  embedding_model: {
    load(value) {
      return cleanLoadedString(value, DEFAULT_CONFIG.embedding_model);
    },
    save(value, currentConfig) {
      return cleanIncomingString(value, currentConfig.embedding_model || DEFAULT_CONFIG.embedding_model);
    }
  },
  embedding_api_key: { load: normalizeLoadedSecret },
  port: { load: normalizePort, save: normalizePort },
  theme: { load: normalizeTheme, save: normalizeTheme },
  admin_secret: { load: normalizeLoadedSecret },
  context_limit: { load: normalizeContextLimit, save: normalizeContextLimit }
};

function normalizeKnownFields(source, mode, currentConfig = DEFAULT_CONFIG) {
  const normalized = {};
  for (const field of mode === "save" ? EDITABLE_CONFIG_FIELDS : STORED_CONFIG_FIELDS) {
    const policy = FIELD_POLICY[field];
    if (mode === "save" && !hasOwnField(source, field)) {
      normalized[field] = policy.load(currentConfig?.[field]);
      continue;
    }
    normalized[field] = mode === "save" ? policy.save(source[field], currentConfig, field, source) : policy.load(source[field]);
  }
  return normalized;
}

export function normalizeLoadedConfig(parsed) {
  if (!isPlainObject(parsed)) {
    return { ...DEFAULT_CONFIG };
  }

  const merged = { ...DEFAULT_CONFIG, ...parsed };
  return {
    ...merged,
    ...normalizeKnownFields(merged, "load")
  };
}

export function pickStoredContractConfig(config) {
  const source = isPlainObject(config) ? { ...DEFAULT_CONFIG, ...config } : { ...DEFAULT_CONFIG };
  return normalizeKnownFields(source, "load");
}

export function buildStoredConfigBase(payload, currentConfig) {
  const normalizedCurrentConfig = pickStoredContractConfig(currentConfig);
  const safePayload = isPlainObject(payload) ? payload : {};
  return {
    ...normalizedCurrentConfig,
    ...normalizeKnownFields(safePayload, "save", normalizedCurrentConfig)
  };
}

export function filterSecretPayload(payload) {
  if (!isPlainObject(payload)) {
    return {};
  }
  return SECRET_FIELDS.reduce((updates, field) => {
    updates[field] = payload[field];
    return updates;
  }, {});
}
