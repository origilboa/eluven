export const vpc = new sst.aws.Vpc.v1("EluvenVpc", {
  nat: "ec2",
});
export const db = new sst.aws.Postgres.v1("Database", {
  vpc,
  scaling: {
    min: "0.5 ACU",
    max: "4 ACU",
  },
});
