
const mermaid = require('mermaid');
const fs = require('fs');

async function validate() {
  const code = fs.readFileSync(0, 'utf-8');
  try {
    mermaid.default.mermaidAPI.initialize({ startOnLoad: false });
    await mermaid.default.parse(code);
    console.log("VALID");
    process.exit(0);
  } catch (err) {
    console.error(err.message || err.toString());
    process.exit(1);
  }
}
validate();
                    