import assert from 'node:assert/strict';
import test from 'node:test';
import { fileInfo, imageSourceInfo, auditDelta } from './image-policy.mjs';
const policy={maxBytes:2,mimetypes:['image/png','image/jpeg']};
test('File limits include the exact boundary and reject one byte over',()=>{
 assert.equal(fileInfo({size:1,type:'image/png'},policy).ok,true);
 assert.equal(fileInfo({size:2,type:'image/png'},policy).ok,true);
 assert.equal(fileInfo({size:3,type:'image/png'},policy).ok,false);
 assert.equal(fileInfo({size:1,type:'image/gif'},policy).ok,false);
});
test('dataURL policy counts decoded bytes rather than base64 characters',()=>{
 for(const [src,bytes,ok] of [['YQ==',1,true],['YWI=',2,true],['YWJj',3,false]]){
  const result=imageSourceInfo('data:image/png;base64,'+src,policy);
  assert.equal(result.bytes,bytes);assert.equal(result.ok,ok);
 }
 for(const source of ['https://example.invalid/picture.png','data:image/gif;base64,YQ==','data:image/png;base64,YQ=','data:image/png;base64,!@#$','data:image/png,plain']) assert.equal(imageSourceInfo(source,policy).ok,false,source);
});
test('export audit reports image positions without changing existing content',()=>{
 const delta={ops:[{insert:'Hello ',attributes:{bold:true}},{insert:{image:'data:image/png;base64,YWI='}},{insert:'\n'},{insert:{image:'data:image/png;base64,YWJj'}}]};
 const before=JSON.stringify(delta);const issues=auditDelta(delta,policy);
 assert.equal(issues.length,1);assert.equal(issues[0].index,8);assert.equal(JSON.stringify(delta),before);
 assert.equal(auditDelta({ops:[{insert:{image:'https://example.invalid/p.png'}}]},policy).length,1);
});
