export const APP_NAME = "Azure Data Copilot";
export const APP_TAGLINE = "AI-powered analytics on your data";

export const POWER_BI_STORAGE_KEY = "sih-powerbi-url";
export const AZURE_SQL_STORAGE_KEY = "sih-azure-sql-config";
export const THEME_STORAGE_KEY = "sih-theme";
export const CHAT_STORAGE_KEY = "sih-workspace-chat";
export const SQL_SESSION_KEY = "sih-sql-agent-session";
export const SQL_SESSION_META_KEY = "sih-sql-agent-meta";
export const SQL_NEEDS_CONFIG_KEY = "sih-sql-needs-config";
export const SQL_SESSION_CHANGED_EVENT = "sih-sql-session-changed";
export const DEVELOPER_MODE_STORAGE_KEY = "sih-developer-mode";
export const DEVELOPER_MODE_CHANGED_EVENT = "sih-developer-mode-changed";

export const SEMICONDUCTOR_CHIPS = [
  { label: "Overall Summary", prompt: "Give overall production summary." },
  { label: "Monthly Yield", prompt: "Show monthly yield." },
  { label: "Compare Sensors", prompt: "Compare Sensor 160 and Sensor 162." },
  { label: "Recommendations", prompt: "Give recommendations." },
  { label: "Explain Dataset", prompt: "What is the SECOM dataset?" },
  { label: "Explain ETL", prompt: "Explain Bronze Silver Gold ETL." },
] as const;

export const GENERIC_SQL_CHIPS = [
  { label: "Dataset Overview", prompt: "What is this dataset about?" },
  { label: "Explain Tables", prompt: "Explain every table." },
  { label: "Production KPIs", prompt: "How many passed wafers?" },
  { label: "Sample Rows", prompt: "Show sample rows." },
] as const;

export const SEMICONDUCTOR_ERROR_SUGGESTIONS = [
  "Give overall production summary",
  "What is the SECOM dataset?",
  "Compare Sensor 160 and Sensor 162",
  "Explain Bronze Silver Gold ETL",
];

export const GENERIC_SQL_ERROR_SUGGESTIONS = [
  "List the tables and views in this database",
  "Show a sample of 10 rows from an important table",
  "Summarize what this database appears to contain",
];

export const WELCOME_TOPICS = [
  "Semiconductor Manufacturing",
  "Azure SQL",
  "ETL Pipelines",
  "Power BI",
  "Databricks",
  "Manufacturing Yield",
  "Sensors",
] as const;
