import { GoogleGenAI } from '@google/genai';
import * as fs from 'fs';
import * as path from 'path';

const ai = new GoogleGenAI(); // Automatically picks up process.env.GEMINI_API_KEY

// Folders to ignore to save tokens
const IGNORE_DIRS = ['node_modules', '.git', '.next', 'dist', 'build'];
const ALLOWED_EXTENSIONS = ['.js', '.jsx', '.ts', '.tsx', '.json', '.css', '.md'];

function readFolder(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);

    if (stat.isDirectory()) {
      if (!IGNORE_DIRS.includes(file)) {
        readFolder(fullPath, fileList);
      }
    } else {
      const ext = path.extname(file);
      if (ALLOWED_EXTENSIONS.includes(ext)) {
        fileList.push(fullPath);
      }
    }
  }
  return fileList;
}

async function run() {
  const targetDir = process.argv[2] || '.';
  console.log(`Scanning folder: ${path.resolve(targetDir)}...`);
  
  const files = readFolder(targetDir);
  let codebaseText = "";

  for (const file of files) {
    const content = fs.readFileSync(file, 'utf8');
    codebaseText += `\n\n--- FILE: ${file} ---\n${content}`;
  }

  console.log(`Sending ${files.files} files to Gemini for analysis...`);

  const response = await ai.models.generateContent({
    model: 'gemini-2.5-pro',
    contents: [
      {
        role: 'user',
        parts: [
          { text: "Please analyze this complete codebase, explain its architecture, point out any potential bugs, and suggest improvements:" },
          { text: codebaseText }
        ]
      }
    ]
  });

  console.log("\n--- GEMINI ANALYSIS ---");
  console.log(response.text);
}

run().catch(console.error);