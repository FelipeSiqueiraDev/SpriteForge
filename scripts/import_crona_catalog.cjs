// Importa somente as duas listas de definições do código confiável do CRONA.
// Não inicia servidor, banco ou cena e não depende do projeto Node do jogo.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

function arrayLiteral(source, name) {
  const match = new RegExp('(?:export\\s+)?const\\s+' + name + '[^=]*=\\s*\\[').exec(source);
  if (!match) throw new Error('Lista não encontrada: ' + name);
  const start = match.index + match[0].lastIndexOf('[');
  let depth = 0, quote = null, lineComment = false, blockComment = false;
  for (let i=start; i<source.length; i++) {
    const ch=source[i], next=source[i+1];
    if (lineComment) { if(ch==='\n')lineComment=false; continue; }
    if (blockComment) { if(ch==='*'&&next==='/'){blockComment=false;i++;} continue; }
    if (quote) { if(ch==='\\'){i++;continue;} if(ch===quote)quote=null; continue; }
    if(ch==='/'&&next==='/'){lineComment=true;i++;continue;}
    if(ch==='/'&&next==='*'){blockComment=true;i++;continue;}
    if(ch==='"'||ch==="'"||ch==='`'){quote=ch;continue;}
    if(ch==='[')depth++;
    if(ch===']'&&--depth===0) return source.slice(start,i+1);
  }
  throw new Error('Lista incompleta: ' + name);
}

function importCatalog(source) {
  function read(name) {
    const literal=arrayLiteral(source,name).replace(/\s+as\s+\[number,\s*number\]/g,'');
    const value=vm.runInNewContext('const ALL=[0,2,4,6]; ('+literal+')',{}, {timeout:1000});
    return JSON.parse(JSON.stringify(value));
  }
  const objects=[...read('FURNI_METERS').map(definition=>({type:'floor',definition})),
                 ...read('WALL_FURNI_LIST').map(definition=>({type:'wall',definition}))];
  const ids=new Set();
  for(const item of objects){
    if(!item.definition.id||ids.has(item.definition.id))throw new Error('ID ausente ou duplicado: '+item.definition.id);
    ids.add(item.definition.id);
    item.id=item.definition.id; item.name=item.definition.name;
  }
  return {version:1,repository:'FelipeSiqueiraDev/CRONA',
    source_sha256:crypto.createHash('sha256').update(source).digest('hex'),
    height_unit:'metres for floor definitions; wall dimensions are native pixels',objects};
}

if(require.main===module){
  const input=process.argv[2],output=process.argv[3];
  if(!input||!output)throw new Error('Uso: node scripts/import_crona_catalog.cjs shared/src/furni.ts catalog.json');
  const data=importCatalog(fs.readFileSync(input,'utf8'));
  fs.mkdirSync(path.dirname(output),{recursive:true});
  fs.writeFileSync(output,JSON.stringify(data,null,2)+'\n');
  console.log('Catálogo importado: '+data.objects.length+' objetos');
}
module.exports={arrayLiteral,importCatalog};
