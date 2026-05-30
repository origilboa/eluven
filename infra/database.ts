export const vpc = new sst.aws.Vpc("EluvenVpc", {
  nat: "ec2",
});

export const db = new sst.aws.Postgres("Database", {
  vpc,
  scaling: {
    min: "0.5 ACU",
    max: "4 ACU",
  },
});
