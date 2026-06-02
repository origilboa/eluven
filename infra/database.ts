export const vpc = new sst.aws.Vpc("EluvenVpc");

export const db = new sst.aws.Postgres("Database", {
  vpc,
  instance: "t3.micro",
  multiAz: false,
});
