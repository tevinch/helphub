import React, {useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import ReactQuill, {Quill} from 'react-quill-new';
import katex from 'katex';
import {toArticleContent,toDelta,validateContent} from './content.mjs';
import 'react-quill-new/dist/quill.snow.css';
import 'katex/dist/katex.min.css';
import './style.css';

// Quill's built-in formula format requires this before the editor is created.
window.katex = katex;
const modules={toolbar:false};
const formats=['formula','link','blockquote','image'];

function Formula({source,displayMode=false}) {
  try {
    const html=katex.renderToString(source,{displayMode,throwOnError:true,trust:false});
    return <span className="equation" data-source={source} dangerouslySetInnerHTML={{__html:html}}/>;
  }catch(error){return <span className="math-error" role="note">Could not render equation: <code>{source}</code></span>;}
}
function Article({content}) {
  validateContent(content);
  return <article aria-label="Saved article">{content.map((paragraph,p)=>{
    if(paragraph.length===1&&paragraph[0].contentType==='pull_quote')return <blockquote key={p}>{paragraph[0].content}</blockquote>;
    const display=paragraph.length===1&&paragraph[0].contentType==='formula';
    return <div className="paragraph" key={p}>{paragraph.length?paragraph.map((segment,s)=>{
      if(segment.contentType==='formula')return <Formula key={s} source={segment.content} displayMode={display}/>;
      if(segment.contentType==='link')return <a key={s} href={segment.href}>{segment.content}</a>;
      if(segment.contentType==='image')return <img key={s} src={segment.content} alt="Article illustration"/>;
      return <React.Fragment key={s}>{segment.content}</React.Fragment>;
    }):<br/>}</div>;
  })}</article>;
}
function App(){
  const editor=useRef(null),lastRange=useRef(null),selected=useRef(null);
  const [article,setArticle]=useState(null),[value,setValue]=useState(null),[source,setSource]=useState(''),[editing,setEditing]=useState(false);
  const [status,setStatus]=useState('Loading article...'),[readOnly,setReadOnly]=useState(false),[saving,setSaving]=useState(false);
  async function load(){
    try{
      const response=await fetch('/article');if(!response.ok)throw new Error('Could not load the article.');
      const data=await response.json();validateContent(data.articleContent);
      setArticle(data);setValue(toDelta(data.articleContent));setStatus('Article loaded.');selected.current=null;setEditing(false);
    }catch(error){setStatus(error.message);}
  }
  useEffect(()=>{load();},[]);
  function selectFormula(event){
    const element=event.target.closest('.ql-formula');if(!element||!editor.current)return;
    const quill=editor.current.getEditor(),blot=Quill.find(element);
    const index=quill.getIndex(blot),op=quill.getContents(index,1).ops[0];
    if(!op?.insert?.formula)return;
    selected.current={index,source:op.insert.formula};setEditing(true);setSource(op.insert.formula);
  }
  function writeFormula(replace){
    if(readOnly)return;
    try{
      if(!source.trim())throw new Error('Enter a TeX equation first.');
      katex.renderToString(source,{throwOnError:true,trust:false});
      const quill=editor.current.getEditor();
      let index;
      if(replace){
        const choice=selected.current;if(!choice)throw new Error('Click an equation in the editor first.');
        if(quill.getContents(choice.index,1).ops[0]?.insert?.formula!==choice.source)throw new Error('The document changed. Select the equation again.');
        index=choice.index;
        // One native Delta replaces the embed without an intermediate lost equation.
        const Delta=Quill.import('delta');
        quill.updateContents(new Delta().retain(index).delete(1).insert({formula:source}),'user');
      }else{
        index=Math.min(lastRange.current?.index??quill.getLength()-1,quill.getLength()-1);
        quill.insertEmbed(index,'formula',source,'user');
      }
      quill.setSelection(index+1,0,'user');quill.focus();
      selected.current=null;setEditing(false);setStatus(replace?'Equation updated.':'Equation inserted.');
    }catch(error){setStatus(error.message);}
  }
  async function save(){
    if(readOnly||saving)return;
    setSaving(true);
    try{
      // This is the full document, not ReactQuill's incremental onChange Delta.
      const articleContent=toArticleContent(editor.current.getEditor().getContents());
      const response=await fetch('/article',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({...article,articleContent})});
      const saved=await response.json();if(!response.ok)throw new Error(saved.error||'Save failed.');
      validateContent(saved.articleContent);setArticle(saved);setStatus('Article saved. Reload to reopen it.');
    }catch(error){setStatus('Save failed: '+error.message);}
    finally{setSaving(false);}
  }
  return <main><h1>Article equations</h1><p>Write normally. Enter TeX without dollar delimiters to insert an equation. Click an existing equation to edit its source.</p>
    <label className="permission"><input type="checkbox" checked={readOnly} onChange={e=>setReadOnly(e.target.checked)}/> Read-only editor</label>
    <fieldset disabled={readOnly||!article}><legend>Equation</legend>
      <label htmlFor="tex">TeX source</label><input id="tex" value={source} onChange={e=>setSource(e.target.value)} placeholder={'\\frac{a}{b}'}/>
      <button type="button" onClick={()=>writeFormula(false)}>Insert equation</button>
      <button type="button" disabled={!editing} onClick={()=>writeFormula(true)}>Replace selected equation</button>
    </fieldset>
    {value&&<section aria-label="Article editor" onClick={selectFormula}><ReactQuill ref={editor} value={value} readOnly={readOnly} modules={modules} formats={formats}
      onChange={(_html,_change,_origin,quill)=>setValue(quill.getContents())}
      onChangeSelection={range=>{if(range)lastRange.current=range;}}/></section>}
    <div className="actions"><button type="button" disabled={readOnly||!article||saving} onClick={save}>Save article</button><button type="button" onClick={load}>Reopen saved article</button></div>
    <p role="status">{status}</p>
    {article&&<><h2>Saved article</h2><Article content={article.articleContent}/><details><summary>Stored JSON</summary><pre>{JSON.stringify(article,null,2)}</pre></details></>}
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);

