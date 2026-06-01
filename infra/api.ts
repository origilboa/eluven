import { vpc, db } from "./database";
import { documentProcessingQueue, workflowExecutionQueue } from "./queues";
import { anthropicApiKey, dbPassword, nextAuthSecret } from "./secrets";
import { documentsBucket } from "./storage";

export const api = new sst.aws.Service("Api", {
  vpc,
  link: [
    db,
    documentsBucket,
    documentProcessingQueue,
    workflowExecutionQueue,
    anthropicApiKey,
    dbPassword,
    nextAuthSecret,
  ],
  image: {
    context: "./backend",
    dockerfile: "Dockerfile",
  },
  port: 8000,
  scaling: {
    min: 1,
    max: 2,
  },
  permissions: [
    {
      actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      resources: ["*"],
    },
  ],
  environment: {
    DATABASE_URL: $interpolate`postgresql://${db.username}:${db.password}@${db.host}:${db.port}/${db.database}`,
    NEXTAUTH_SECRET: nextAuthSecret.value,
    S3_DOCUMENTS_BUCKET: documentsBucket.name,
    DOCUMENT_PROCESSING_QUEUE_URL: documentProcessingQueue.url,
    WORKFLOW_EXECUTION_QUEUE_URL: workflowExecutionQueue.url,
    AWS_REGION: "us-east-1",
    ENVIRONMENT: $app.stage,
    LOG_LEVEL: "INFO",
  },
  dev: {
    command: "poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000",
    directory: "./backend",
    url: "http://localhost:8000",
  },
});
