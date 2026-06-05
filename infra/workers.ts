import { bedrockPermissions } from "./bedrock-permissions";
import { cluster } from "./api";
import { db } from "./database";
import { documentProcessingQueue, workflowExecutionQueue } from "./queues";
import { anthropicApiKey, dbPassword, nextAuthSecret } from "./secrets";
import { documentsBucket } from "./storage";

const backendImage = {
  context: ".",
  dockerfile: "backend/Dockerfile",
};

const workerEnvironment = {
  DATABASE_URL: $interpolate`postgresql+asyncpg://${db.username}:${db.password}@${db.host}:${db.port}/${db.database}`,
  NEXTAUTH_SECRET: nextAuthSecret.value,
  S3_DOCUMENTS_BUCKET: documentsBucket.name,
  DOCUMENT_PROCESSING_QUEUE_URL: documentProcessingQueue.url,
  WORKFLOW_EXECUTION_QUEUE_URL: workflowExecutionQueue.url,
  AWS_REGION: aws.getRegionOutput().name,
  ENVIRONMENT: $app.stage,
  LOG_LEVEL: "INFO",
  DEFAULT_BEDROCK_MODEL_ID: "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
};

const workerLinks = [
  db,
  documentsBucket,
  documentProcessingQueue,
  workflowExecutionQueue,
  anthropicApiKey,
  dbPassword,
  nextAuthSecret,
];

export const documentWorker = new sst.aws.Service("DocumentWorker", {
  cluster,
  link: workerLinks,
  image: backendImage,
  command: ["python", "-m", "workers.document_worker"],
  scaling: {
    min: 1,
    max: 1,
  },
  permissions: bedrockPermissions,
  environment: workerEnvironment,
  dev: {
    command: "poetry run python -m workers.document_worker",
    directory: "./backend",
  },
});

export const workflowWorker = new sst.aws.Service("WorkflowWorker", {
  cluster,
  link: workerLinks,
  image: backendImage,
  command: ["python", "-m", "workers.workflow_worker"],
  scaling: {
    min: 1,
    max: 1,
  },
  permissions: bedrockPermissions,
  environment: workerEnvironment,
  dev: {
    command: "poetry run python -m workers.workflow_worker",
    directory: "./backend",
  },
});
