import { TBinaryProtocol, TFramedTransport } from "thrift";
import { Config } from "../src/blitz/generated/thrift/gen-nodejs/config_types.js";

if (process.argv.length < 3) {
  console.error("Please provide a binary config file path");
  process.exit(1);
}

const filePath = process.argv[2];
const fileData = fs.readFileSync(filePath);
const base64Data = Buffer.from(fileData, "base64");

try {
  const readTransport = new TFramedTransport(base64Data);
  const readProtocol = new TBinaryProtocol(readTransport);

  const configNew = new Config();
  configNew[Symbol.for("read")](readProtocol);
  console.log("Successfully read config:", JSON.stringify(configNew, null, 2));
} catch (error) {
  console.log("Error reading config:", error.message);
  console.error(error?.stack);
}
