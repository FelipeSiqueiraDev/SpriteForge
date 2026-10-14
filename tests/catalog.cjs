const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {arrayLiteral,importCatalog}=require('../scripts/import_crona_catalog.cjs');

test('Imports a new code object without requiring artwork or changing its definition',()=>{
 const source=`const FURNI_METERS: FurniDef[] = [
 {id:'new',name:'Nova [cadeira]',category:'room',width:1,depth:1,height:0.5,states:2,rotations:ALL,walkable:false},
 ];
 export const WALL_FURNI_LIST: WallFurniDef[] = [{id:'frame',name:'Quadro',category:'wall',w:32,h:40,anchor:[2,3] as [number, number]}];`;
 const catalog=importCatalog(source);
 assert.equal(catalog.objects.length,2);
 assert.deepEqual(catalog.objects[0].definition.rotations,[0,2,4,6]);
 assert.equal(catalog.objects[0].definition.walkable,false);
 assert.equal(catalog.objects[1].type,'wall');
 assert.deepEqual(catalog.objects[1].definition.anchor,[2,3]);
});
test('Extracts nested arrays with comments and quoted brackets',()=>{
 const literal=arrayLiteral("const LIST = [ // ]\n ['[', '\\''], /* [ ] */ [1,2] ];",'LIST');
 assert.ok(literal.endsWith('[1,2] ]'));
 assert.throws(()=>arrayLiteral('const LIST=[1;', 'LIST'),/incompleta/);
});
test('Rejects duplicate IDs across floor and wall',()=>{
 assert.throws(()=>importCatalog("const FURNI_METERS=[{id:'same'}]; const WALL_FURNI_LIST=[{id:'same'}];"),/duplicado/);
});
test('Current snapshot includes the nine recipes without losing gameplay properties',()=>{
 const catalog=JSON.parse(fs.readFileSync('integrations/crona/catalog.json','utf8'));
 const profile=JSON.parse(fs.readFileSync('skins/profiles/crona-cozy-v1.json','utf8'));
 for(const id of profile.recipes){
   const row=catalog.objects.find(r=>r.id===id);
   assert.ok(row,id);
   assert.deepEqual([row.definition.width,row.definition.depth],profile.footprints[id]);
 }
 assert.equal(catalog.objects.find(r=>r.id==='fogao_lenha').definition.states,2);
});
