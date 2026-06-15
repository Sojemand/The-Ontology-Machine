import path from "node:path";

import {
  APP_DIR_NAME,
  APP_HOME_ENV,
  CHAT_DB_COMPANION_SUFFIXES,
  CHATS_DB_FILENAME,
  CONFIG_DIR_NAME,
  CONFIG_FILE_NAME,
  FRONTEND_POLICY_FILE_NAME,
  LOG_DIR_NAME,
  SALT_FILENAME,
  SERVER_STATE_CHAT_FILENAME,
  SERVER_STATE_CONFIG_FILENAME,
  SNAPSHOT_DIR_NAME,
  STATE_DIR_NAME
} from "./types.js";
import { resolveConfiguredAppHome, validateModuleRoot } from "./validation.js";

function dbCompanionPaths(baseDir, fileName) {
  return CHAT_DB_COMPANION_SUFFIXES.map((suffix) => path.join(baseDir, `${fileName}${suffix}`));
}

export function buildAppPaths({
  moduleRoot,
  appHome,
  envAppHome = process.env[APP_HOME_ENV],
  localAppData = process.env.LOCALAPPDATA
} = {}) {
  const resolvedModuleRoot = validateModuleRoot(moduleRoot);
  const resolvedAppHome = resolveConfiguredAppHome(appHome, envAppHome, localAppData);
  const configDir = path.join(resolvedAppHome, CONFIG_DIR_NAME);
  const stateDir = path.join(resolvedAppHome, STATE_DIR_NAME);

  return {
    module_root: resolvedModuleRoot,
    app_home: resolvedAppHome,
    app_dir: path.join(resolvedAppHome, APP_DIR_NAME),
    config_dir: configDir,
    state_dir: stateDir,
    log_dir: path.join(resolvedAppHome, LOG_DIR_NAME),
    config_path: path.join(configDir, CONFIG_FILE_NAME),
    frontend_policy_path: path.join(configDir, FRONTEND_POLICY_FILE_NAME),
    salt_path: path.join(configDir, SALT_FILENAME),
    chats_db_path: path.join(stateDir, CHATS_DB_FILENAME),
    server_state_chat_path: path.join(stateDir, SERVER_STATE_CHAT_FILENAME),
    server_state_config_path: path.join(stateDir, SERVER_STATE_CONFIG_FILENAME),
    snapshot_dir: path.join(resolvedModuleRoot, SNAPSHOT_DIR_NAME),
    legacy_config_path: path.join(resolvedModuleRoot, CONFIG_FILE_NAME),
    legacy_frontend_policy_path: path.join(resolvedModuleRoot, FRONTEND_POLICY_FILE_NAME),
    legacy_salt_path: path.join(resolvedModuleRoot, SALT_FILENAME),
    legacy_log_dir: path.join(resolvedModuleRoot, LOG_DIR_NAME),
    legacy_chat_db_paths: dbCompanionPaths(resolvedModuleRoot, CHATS_DB_FILENAME),
    state_chat_db_paths: dbCompanionPaths(stateDir, CHATS_DB_FILENAME)
  };
}
