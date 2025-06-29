#!/usr/bin/env node
import { execSync } from "child_process";
import fs from "fs";
import path from "path";

const SCHEMA_DIR = "src/config/schema";
const OUTPUT_DIR = "src/blitz/generated/thrift";

function ensureDirectoryExists(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`Created directory: ${dirPath}`);
  }
}

function findThriftFiles(dir) {
  const files = [];
  const items = fs.readdirSync(dir);

  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);

    if (stat.isDirectory()) {
      files.push(...findThriftFiles(fullPath));
    } else if (item.endsWith(".thrift")) {
      files.push(fullPath);
    }
  }

  return files;
}

function generateTypeScript() {
  console.log("🚀 Generating TypeScript from Thrift files...");

  ensureDirectoryExists(OUTPUT_DIR);

  const thriftFiles = findThriftFiles(SCHEMA_DIR);
  console.log(`Found ${thriftFiles.length} Thrift files:`);
  thriftFiles.forEach((file) => console.log(`  - ${file}`));

  try {
    for (const thriftFile of thriftFiles) {
      console.log(`\n📦 Processing: ${thriftFile}`);

      const cmd = `thrift --gen js:ts,node -o ${OUTPUT_DIR} -I ${SCHEMA_DIR} ${thriftFile}`;
      console.log(`Running: ${cmd}`);

      execSync(cmd, { stdio: "inherit" });
    }

    console.log("\n✅ TypeScript generation completed successfully!");
    console.log(`📂 Generated files are in: ${OUTPUT_DIR}`);
  } catch (error) {
    console.error("\n❌ Error generating TypeScript:", error.message);
    process.exit(1);
  }
}

generateTypeScript();
