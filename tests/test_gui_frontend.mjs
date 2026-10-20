/* Exercise frontend accounting with real C bridge replies and execute a copied command. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {spawnSync} from 'node:child_process';

const root=process.cwd();
const option=(name,fallback)=>{const i=process.argv.indexOf(name);return path.resolve(i<0?fallback:process.argv[i+1]);};
const bridge=option('--bridge','build/gui/gui_bridge_stdio.exe');
const cli=option('--cli','build/release/rocketperf.exe');
const context=vm.createContext({TABS:[],finite:(v)=>typeof v==='number'&&Number.isFinite(v)});
vm.runInContext(fs.readFileSync(path.join(root,'src/gui/web/tab_engineering.js'),'utf8')+'\nthis.counts=selfCheckCounts;',context);
const requests=[
 ['chamber_sweep',{fuel:'ch4',pc:1e7,of_min:.5,of_max:4.5,n:81}],
 ['nozzle_sweep',{fuel:'ch4',pc:1e7,of:2.6,at:.01,ars:[2,3,4,5,6,8,10,12,15,20,25,30,40,50,60],pas:[0,5000,50000,101325]}],
 ['compare',{ch4_of:2.6,rp1_of:2.6,ar:10,pa:0,at:.01,of_min:2.2,of_max:4,n:37}],
 ...['zq3_y1_stage1','zq3_y1_stage2','cz10b_first_stage1','cz10b_first_stage2','cz10b_first_stage2_orsc'].map((c)=>['cycle',{case:`cases/vehicles/${c}.ini`}]),
 ['chamber',{fuel:'ch4',of:.8}],
];
const run=spawnSync(bridge,[],{cwd:root,encoding:'utf8',input:requests.map(([cmd,args])=>JSON.stringify({cmd,args})).join('\n')+'\n',timeout:120000});
assert.equal(run.status,0,run.stderr);
const replies=run.stdout.trim().split('\n').map((s)=>JSON.parse(s));
assert.equal(replies.length,requests.length);
const total={solved:0,diagnostic:0,rejected:0,failedCalls:0};
for(let i=0;i<8;i++){
 const [cmd]=requests[i],e=replies[i];assert.equal(e.ok,true);
 const count=context.counts(cmd,e);for(const k of Object.keys(total))total[k]+=count[k];
 if(cmd==='cycle')for(const field of ['mass_relative','shaft_residual','energy_residual'])assert.ok(Number.isFinite(e.result.balance[field]),field);
}
assert.equal(total.solved+total.diagnostic+total.rejected,184);
assert.ok(total.diagnostic>0&&total.rejected>0);
assert.equal(total.failedCalls,0);
const failed=context.counts('chamber',replies[8]);
assert.equal(failed.solved,0);assert.equal(failed.failedCalls,1);
const core=fs.readFileSync(path.join(root,'src/gui/web/core.js'),'utf8');
// Load the actual command builders without starting the DOM-facing bridge.
vm.runInContext(core.slice(0,core.indexOf('const RP ='))+'\nthis.command=CMD;',context);
const command=context.command.rp1(2.6,10,0);
assert.ok(command.startsWith('./rocketperf.exe '));
const args=command.slice('./rocketperf.exe '.length);
const ps=spawnSync('pwsh',['-NoProfile','-Command',"& $env:RP_FRONTEND_TEST_BINARY "+args],{
 cwd:root,env:{...process.env,RP_FRONTEND_TEST_BINARY:cli},encoding:'utf8',timeout:120000,
});
assert.equal(ps.status,0,ps.stderr);
assert.ok(Math.abs(JSON.parse(ps.stdout).geometry.specific_impulse_s-310.5717)<.001);
console.log(JSON.stringify({status:'PASS',counts:total,cycles:5,copied_rp1_command:'PASS'}));
