export const documentsBucket = new sst.aws.Bucket("Documents", {
  transform: {
    bucket: {
      versioning: { status: "Enabled" },
    },
  },
});
