import { vpc } from "./database";

const region = aws.getRegionOutput().name;

const endpointSecurityGroup = new aws.ec2.SecurityGroup("EluvenVpcEndpointsSecurityGroup", {
  vpcId: vpc.id,
  description: "Allow HTTPS access to VPC interface endpoints",
  ingress: [
    {
      protocol: "tcp",
      fromPort: 443,
      toPort: 443,
      cidrBlocks: [vpc.nodes.vpc.cidrBlock],
    },
  ],
  egress: [
    {
      protocol: "-1",
      fromPort: 0,
      toPort: 0,
      cidrBlocks: ["0.0.0.0/0"],
    },
  ],
});

function interfaceEndpoint(name: string, serviceSuffix: string) {
  return new aws.ec2.VpcEndpoint(name, {
    vpcId: vpc.id,
    serviceName: region.apply((value) => `com.amazonaws.${value}.${serviceSuffix}`),
    vpcEndpointType: "Interface",
    subnetIds: vpc.privateSubnets,
    securityGroupIds: [endpointSecurityGroup.id],
    privateDnsEnabled: true,
  });
}

export const s3Endpoint = new aws.ec2.VpcEndpoint("EluvenVpcS3Endpoint", {
  vpcId: vpc.id,
  serviceName: region.apply((value) => `com.amazonaws.${value}.s3`),
  vpcEndpointType: "Gateway",
  routeTableIds: $resolve([vpc.nodes.privateRouteTables, vpc.nodes.publicRouteTables]).apply(
    ([privateRouteTables, publicRouteTables]) => [
      ...privateRouteTables.map((routeTable) => routeTable.id),
      ...publicRouteTables.map((routeTable) => routeTable.id),
    ],
  ),
});

export const sqsEndpoint = interfaceEndpoint("EluvenVpcSqsEndpoint", "sqs");
export const bedrockEndpoint = interfaceEndpoint("EluvenVpcBedrockRuntimeEndpoint", "bedrock-runtime");
export const secretsManagerEndpoint = interfaceEndpoint(
  "EluvenVpcSecretsManagerEndpoint",
  "secretsmanager",
);
export const ecrApiEndpoint = interfaceEndpoint("EluvenVpcEcrApiEndpoint", "ecr.api");
export const ecrDkrEndpoint = interfaceEndpoint("EluvenVpcEcrDkrEndpoint", "ecr.dkr");
export const logsEndpoint = interfaceEndpoint("EluvenVpcLogsEndpoint", "logs");
export const stsEndpoint = interfaceEndpoint("EluvenVpcStsEndpoint", "sts");
