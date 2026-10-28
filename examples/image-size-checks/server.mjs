import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const files=new Map([
 ['/', ['index.html','text/html']],['/app.mjs',['app.mjs','text/javascript']],
 ['/image-policy.mjs',['image-policy.mjs','text/javascript']],['/image-limits.mjs',['image-limits.mjs','text/javascript']],
 ['/node_modules/quill/dist/quill.js',['node_modules/quill/dist/quill.js','text/javascript']],
 ['/node_modules/quill/dist/quill.snow.css',['node_modules/quill/dist/quill.snow.css','text/css']],
]);
export function createDemoServer(){return createServer(async(req,res)=>{
 const file=files.get(req.url);if(req.method!=='GET'||!file){res.writeHead(404);res.end();return;}
 try{const bytes=await readFile(new URL(file[0],import.meta.url));res.writeHead(200,{'Content-Type':file[1]});res.end(bytes);}catch{res.writeHead(500);res.end('Could not load example');}
});}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)createDemoServer().listen(3000,'127.0.0.1',()=>console.log('Open http://127.0.0.1:3000'));
