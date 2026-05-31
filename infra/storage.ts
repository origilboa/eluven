export const documentsBucket = new sst.aws.Bucket("Documents", {
  versioning: true,
});
