/** IAM permissions for Bedrock model invoke + Marketplace model subscriptions. */
export const bedrockPermissions = [
  {
    actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    resources: ["*"],
  },
  {
    actions: ["aws-marketplace:ViewSubscriptions", "aws-marketplace:Subscribe"],
    resources: ["*"],
  },
];
