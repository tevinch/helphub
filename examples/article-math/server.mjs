import http from 'node:http';
import path from 'node:path';
import { promises as fs } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { validateContent } from './content.mjs';
const root = fileURLToPath(new URL('.', import.meta.url));
export const seedArticle = {
  title:'Article with equations',
  articleContent:[
    [{contentType:'text',content:'Keep this existing α paragraph and literal <b> text. Read '},{contentType:'link',content:'the reference',href:'https://example.org/reference'},{contentType:'text',content:' before adding an equation.'}],
    [{contentType:'pull_quote',content:'Keep this existing pull quote.'}],
    [],
    [{contentType:'text',content:'The equation belongs below.'}]
  ],
  sources:[{text:'Existing source',href:'https://example.org/reference'}]
};
export async function startServer({storePath=path.join(root,'.data/article.json'),port=4178}={}) {
  await fs.mkdir(path.dirname(storePath),{recursive:true});
  try { await fs.access(storePath); } catch { await fs.writeFile(storePath,JSON.stringify(seedArticle,null,2)); }
  const server = http.createServer(async(req,res)=>{
    function json(status,value){res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value));}
    try {
      const pathname = new URL(req.url,'http://localhost').pathname;
      if(pathname==='/article'){
        if(req.method==='GET'){json(200,JSON.parse(await fs.readFile(storePath,'utf8')));return;}
        if(req.method==='PUT'){
          const chunks=[];let size=0;
          for await(const chunk of req){size+=chunk.length;if(size>1_000_000){json(413,{error:'Article is too large.'});return;}chunks.push(chunk);}
          let value;
          try { value=JSON.parse(Buffer.concat(chunks).toString()); validateContent(value.articleContent); }
          catch(error){json(422,{error:error.message});return;}
          await fs.writeFile(storePath+'.tmp',JSON.stringify(value,null,2));
          await fs.rename(storePath+'.tmp',storePath);
          json(200,value);return;
        }
        json(405,{error:'Use GET or PUT.'});return;
      }
      if(req.method!=='GET'){json(405,{error:'Use GET.'});return;}
      const target = pathname==='/'?path.join(root,'index.html'):path.resolve(root,'dist','.'+pathname);
      if(pathname!=='/'&&!target.startsWith(path.join(root,'dist')+path.sep)){json(404,{error:'Not found.'});return;}
      const type={'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf'}[path.extname(target)]||'application/octet-stream';
      const data=await fs.readFile(target);res.writeHead(200,{'Content-Type':type});res.end(data);
    }catch(error){json(error.code==='ENOENT'?404:500,{error:error.code==='ENOENT'?'Not found.':'Could not read or save the article.'});}
  });
  await new Promise(resolve=>server.listen(port,'127.0.0.1',resolve));
  return server;
}
if(process.argv[1]===fileURLToPath(import.meta.url)){const s=await startServer({port:Number(process.env.PORT||4178)});console.log('Article equations: http://127.0.0.1:'+s.address().port);}

