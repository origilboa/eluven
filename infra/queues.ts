export const documentProcessingQueue = new sst.aws.Queue("DocumentProcessing", {
  transform: {
    queue: {
      visibilityTimeoutSeconds: 300,
      messageRetentionSeconds: 86400,
    },
  },
});

export const workflowExecutionQueue = new sst.aws.Queue("WorkflowExecution", {
  transform: {
    queue: {
      visibilityTimeoutSeconds: 600,
      messageRetentionSeconds: 86400,
    },
  },
});
