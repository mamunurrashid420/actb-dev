import { createRequire } from "node:module";

type ConnectionType = "postgres" | "mysql" | "bigquery";
type ConnectionConfig = Record<string, unknown>;

type TestConnectionResult =
  | { ok: true }
  | {
      ok: false;
      message: string;
    };

const DEFAULT_TIMEOUT_MS = 10_000;
const requireModule = createRequire(import.meta.url);

const withTimeout = async <T>(
  promise: Promise<T>,
  timeoutMs: number,
  label: string,
): Promise<T> => {
  let timeout: NodeJS.Timeout | null = null;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeout = setTimeout(
      () => reject(new Error(`${label} timed out after ${timeoutMs}ms`)),
      timeoutMs,
    );
  });
  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timeout) clearTimeout(timeout);
  }
};

const getString = (value: unknown) => (typeof value === "string" ? value.trim() : "");
const getNumber = (value: unknown) =>
  typeof value === "number" ? value : Number(value);
const getBoolean = (value: unknown) => (typeof value === "boolean" ? value : undefined);

const requireFields = (fields: Array<[string, string]>) => {
  const missing = fields
    .filter(([, value]) => value.length === 0)
    .map(([label]) => label);
  if (missing.length > 0) {
    return `Missing required fields: ${missing.join(", ")}`;
  }
  return null;
};

const formatMissingDependency = (error: unknown, moduleName: string) => {
  if (
    error &&
    typeof error === "object" &&
    "code" in error &&
    error.code === "MODULE_NOT_FOUND"
  ) {
    return `Missing server dependency: ${moduleName}. Install it to enable connection tests.`;
  }
  return null;
};

async function testPostgresConnection(
  config: ConnectionConfig,
): Promise<TestConnectionResult> {
  const host = getString(config.host);
  const database = getString(config.database);
  const username = getString(config.username);
  const password = getString(config.password);
  const port = getNumber(config.port || 5432);
  const ssl = getBoolean(config.ssl);

  const missing = requireFields([
    ["host", host],
    ["database", database],
    ["username", username],
    ["password", password],
  ]);
  if (missing) return { ok: false, message: missing };

  let client: any;
  try {
    const { Client } = requireModule("pg") as { Client: new (...args: any[]) => any };
    client = new Client({
      host,
      port,
      database,
      user: username,
      password,
      ssl: ssl ? { rejectUnauthorized: false } : undefined,
    });
    await withTimeout(client.connect(), DEFAULT_TIMEOUT_MS, "Postgres connect");
    await withTimeout(client.query("select 1"), DEFAULT_TIMEOUT_MS, "Postgres ping");
    return { ok: true };
  } catch (error) {
    const dependencyMessage = formatMissingDependency(error, "pg");
    if (dependencyMessage) {
      return { ok: false, message: dependencyMessage };
    }
    const message = error instanceof Error ? error.message : "Unknown Postgres error";
    return { ok: false, message };
  } finally {
    if (client) {
      try {
        await client.end();
      } catch {
        // Ignore cleanup errors
      }
    }
  }
}

async function testMysqlConnection(
  config: ConnectionConfig,
): Promise<TestConnectionResult> {
  const host = getString(config.hostname || config.host);
  const database = getString(config.database);
  const username = getString(config.username);
  const password = getString(config.password);
  const port = getNumber(config.port || 3306);
  const ssl = getBoolean(config.ssl);

  const missing = requireFields([
    ["hostname", host],
    ["database", database],
    ["username", username],
    ["password", password],
  ]);
  if (missing) return { ok: false, message: missing };

  let connection: any;
  try {
    const mysql = requireModule("mysql2/promise") as {
      createConnection: (...args: any[]) => Promise<any>;
    };
    connection = await withTimeout(
      mysql.createConnection({
        host,
        port,
        user: username,
        password,
        database,
        ssl: ssl ? {} : undefined,
      }),
      DEFAULT_TIMEOUT_MS,
      "MySQL connect",
    );
    await withTimeout(connection.query("select 1"), DEFAULT_TIMEOUT_MS, "MySQL ping");
    return { ok: true };
  } catch (error) {
    const dependencyMessage = formatMissingDependency(error, "mysql2");
    if (dependencyMessage) {
      return { ok: false, message: dependencyMessage };
    }
    const message = error instanceof Error ? error.message : "Unknown MySQL error";
    return { ok: false, message };
  } finally {
    if (connection) {
      try {
        await connection.end();
      } catch {
        // Ignore cleanup errors
      }
    }
  }
}

async function testBigQueryConnection(
  config: ConnectionConfig,
): Promise<TestConnectionResult> {
  const projectId = getString(config.project_id);
  const datasetId = getString(config.dataset_id);
  const credentialsJson = getString(config.credentials_json);
  const keyFilePath = getString(config.key_file_path);

  const missing = requireFields([["project_id", projectId]]);
  if (missing) return { ok: false, message: missing };

  try {
    const { BigQuery } = requireModule("@google-cloud/bigquery") as {
      BigQuery: new (...args: any[]) => any;
    };
    let credentials: Record<string, unknown> | undefined;

    if (credentialsJson) {
      try {
        credentials = JSON.parse(credentialsJson);
      } catch {
        return { ok: false, message: "Invalid credentials_json. Must be valid JSON." };
      }
    }

    const client = new BigQuery({
      projectId,
      credentials,
      keyFilename: keyFilePath || undefined,
    });

    if (datasetId) {
      await withTimeout(
        client.dataset(datasetId).get(),
        DEFAULT_TIMEOUT_MS,
        "BigQuery dataset check",
      );
    } else {
      await withTimeout(
        client.getDatasets({ maxResults: 1 }),
        DEFAULT_TIMEOUT_MS,
        "BigQuery list datasets",
      );
    }

    return { ok: true };
  } catch (error) {
    const dependencyMessage = formatMissingDependency(error, "@google-cloud/bigquery");
    if (dependencyMessage) {
      return { ok: false, message: dependencyMessage };
    }
    const message = error instanceof Error ? error.message : "Unknown BigQuery error";
    return { ok: false, message };
  }
}

export async function testDatabaseConnection(
  type: ConnectionType,
  config: ConnectionConfig,
): Promise<TestConnectionResult> {
  switch (type) {
    case "postgres":
      return testPostgresConnection(config);
    case "mysql":
      return testMysqlConnection(config);
    case "bigquery":
      return testBigQueryConnection(config);
    default:
      return { ok: false, message: "Unsupported database type" };
  }
}
