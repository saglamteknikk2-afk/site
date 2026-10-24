'use strict';
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf','.xml':'application/xml','.txt':'text/plain; charset=utf-8'};
function resolveFile(directory,base,pathname){
 let decoded;try{decoded=decodeURIComponent(pathname);}catch(_){return null;}
 if(base&&decoded!==base&&!decoded.startsWith(base+'/'))return null;
 let relative=(base?decoded.slice(base.length):decoded).replace(/^\//,'');if(!relative||relative.endsWith('/'))relative+='index.html';
 const file=path.resolve(directory,relative);return file.startsWith(directory+path.sep)&&fs.existsSync(file)&&fs.statSync(file).isFile()?{file,relative}:null;
}
async function startServer(directory,base){
 directory=path.resolve(directory);const errors=[],cache=new Map();let requests=0;
 const server=http.createServer((req,res)=>{requests++;const u=new URL(req.url,'http://local');if(base&&u.pathname===base){res.writeHead(301,{Location:base+'/'});return res.end();}const resolved=resolveFile(directory,base,u.pathname),status=/\.php(?:$|\/)/i.test(u.pathname)?403:resolved?200:404;if(status>=400)errors.push({path:u.pathname,status});const file=status===200?resolved.file:path.join(directory,'404.html');if(!cache.has(file))cache.set(file,fs.readFileSync(file));const body=cache.get(file);res.writeHead(status,{'Content-Type':status===200?(mime[path.extname(file)]||'application/octet-stream'):'text/html; charset=utf-8','Content-Length':body.length,'Cache-Control':'no-cache'});res.end(req.method==='HEAD'?undefined:body);});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));return {origin:'http://127.0.0.1:'+server.address().port,errors,get requests(){return requests;},close:()=>new Promise(resolve=>server.close(resolve))};
}
const publicNames=directory=>fs.readdirSync(directory).filter(n=>n.endsWith('.html')&&n!=='owner-admin.html'&&!/^(?:google|yandex_)/.test(n)).sort();
module.exports={startServer,resolveFile,publicNames,mime};
