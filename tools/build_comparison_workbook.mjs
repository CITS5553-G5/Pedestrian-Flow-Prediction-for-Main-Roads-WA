import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
// ARTIFACT_NODE_MODULES may point to an existing compatible artifact runtime.
const require = createRequire(import.meta.url);
const resolved = require.resolve('@oai/artifact-tool', {paths:[process.env.ARTIFACT_NODE_MODULES ?? process.cwd()]});
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(resolved).href);

const input = process.argv[2], out = process.argv[3] ?? input;
if (!input) throw new Error('Usage: node tools/build_comparison_workbook.mjs <evaluation-json-directory> [workbook-directory]');
await fs.mkdir(out,{recursive:true});
try { await fs.access(`${out}/irap_comparison.xlsx`); throw new Error('Workbook already exists; use a new output directory.'); } catch(e) { if(e.code !== 'ENOENT') throw e; }
const payload = JSON.parse(await fs.readFile(`${input}/comparison.json`, 'utf8'));
const wb = Workbook.create();
const summary = wb.worksheets.add('Summary');
const sites = wb.worksheets.add('Site_Comparison');
const errors = wb.worksheets.add('Errors');
const definitions = wb.worksheets.add('Definitions');
const navy = '#203850', blue = '#2864A0', orange = '#C56B2D';
const font = 'Arial';
const fields = [
  ['site_id','Site ID','',14],
  ['road_no','Road number','',14],
  ['slk_km','SLK (km)','km',12],
  ['source_location_id','Client source location ID','',24],
  ['obs_peak_cross_ped_per_h','Observed peak-hour flow — Crossing','pedestrians/hour',22],
  ['pred_peak_cross_ped_per_h','Model-predicted peak-hour flow — Crossing','pedestrians/hour',23],
  ['existing_irap_cross_recoded_ped_per_h','Existing iRAP flow estimate (recoded) — Crossing','pedestrians/hour',29],
  ['observed_cross_category','Observed flow category — Crossing','category',17],
  ['predicted_cross_category','Model-predicted flow category — Crossing','category',19],
  ['existing_ausrap_cross_category','Existing AusRAP flow category — Crossing','category',19],
  ['existing_ausrap_cross_band','Existing AusRAP flow band — Crossing','pedestrians/hour',24],
  ['obs_peak_along_ped_per_h','Observed peak-hour flow — Along-road','pedestrians/hour',23],
  ['pred_peak_along_ped_per_h','Model-predicted peak-hour flow — Along-road','pedestrians/hour',24],
  ['existing_irap_along_recoded_ped_per_h','Existing iRAP flow estimate (recoded) — Along-road','pedestrians/hour',29],
  ['existing_ausrap_along_combined_band','Existing AusRAP combined flow band — Along-road','pedestrians/hour',27],
  ['cross_evaluation_eligible','Included in crossing metrics','boolean',20],
  ['along_evaluation_eligible','Included in along-road metrics','boolean',20],
  ['comparison_status','Comparison status','',24],
  ['comparison_notes','Comparison notes','',68],
];
const col = n => { let s = ''; for (; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + (n - 1) % 26) + s; return s; };
function base(sheet, range) {
  sheet.showGridLines = false;
  sheet.getRange(range).format.font = {name:font,size:10,color:'#20303E'};
  sheet.getRange(range).format.verticalAlignment = 'center';
  sheet.getRange(range).format.rowHeight = 22;
}
function header(sheet, range) {
  sheet.getRange(range).format.fill = navy;
  sheet.getRange(range).format.font = {name:font,size:10,bold:true,color:'#FFFFFF'};
  sheet.getRange(range).format.wrapText = true;
  sheet.getRange(range).format.horizontalAlignment = 'center';
}
const end = payload.sites.length + 1;
base(sites, `A1:S${end}`);
sites.getRange(`A1:S${end}`).values = [fields.map(f=>f[1]), ...payload.sites.map(r=>fields.map(f=>r[f[0]] ?? null))];
for(let j=0;j<fields.length;j++) sites.getRange(`${col(j+1)}1:${col(j+1)}${end}`).format.columnWidth=fields[j][3];
header(sites,'A1:S1'); sites.getRange('A1:S1').format.rowHeight=78;
sites.getRange(`C2:C${end}`).setNumberFormat('0.000');
for(const r of [`E2:G${end}`,`L2:N${end}`])sites.getRange(r).setNumberFormat('0.00');
sites.getRange(`H2:J${end}`).setNumberFormat('0');
sites.getRange(`S2:S${end}`).format.wrapText=true;
for(let i=0;i<payload.sites.length;i++)sites.getRange(`A${i+2}:S${i+2}`).format.rowHeight=payload.sites[i].comparison_notes.length>100?56:32;
sites.freezePanes.freezeRows(1); sites.freezePanes.freezeColumns(1);
sites.tables.add(`A1:S${end}`,true,'SurveyComparison').style='TableStyleLight1';
for(const c of ['K','O'])sites.getRange(`${c}2:${c}${end}`).format.horizontalAlignment='center';
sites.getRange(`H2:J${end}`).format.horizontalAlignment='center';
for(const c of ['P','Q'])sites.getRange(`${c}2:${c}${end}`).conditionalFormats.add('cellIs',{operator:'equal',formula:'FALSE',format:{fill:'#FFF1DA',font:{color:'#7F4A12'}}});

// Sort the two eligible groups into contiguous ranges for the two XY plots.
// Every survey-direction row, including exclusions, remains in Errors.
const errorRows=[...payload.errors].sort((a,b)=>Number(b.eligible)-Number(a.eligible)||['Cross-road','Along-road'].indexOf(a.direction)-['Cross-road','Along-road'].indexOf(b.direction)||a.site_id.localeCompare(b.site_id));
const errorEnd=errorRows.length+1;
base(errors,`A1:M${errorEnd}`);
errors.getRange('A1:M1').values=[['Site ID','Direction','Observed flow','Model (road-grouped OOF)','Existing iRAP flow estimate (recoded)','Included (1=yes, 0=no)','Model error','Model absolute error','Model squared error','Existing estimate error','Existing estimate absolute error','Existing estimate squared error','Exclusion reason']];
header(errors,'A1:M1');errors.getRange('A1:M1').format.rowHeight=60;
errors.getRange(`A1:L${errorEnd}`).format.columnWidth=19;
errors.getRange(`M1:M${errorEnd}`).format.columnWidth=52;
errors.freezePanes.freezeRows(1);errors.freezePanes.freezeColumns(2);
errors.getRange(`C2:E${errorEnd}`).setNumberFormat('0.00');
errors.getRange(`G2:L${errorEnd}`).setNumberFormat('0.00');
const lookup=(r,c,blank=false)=>{
  const x=`INDEX('Site_Comparison'!$${c}$2:$${c}$${end},MATCH($A${r},'Site_Comparison'!$A$2:$A$${end},0))`;
  return blank?`IF(ISBLANK(${x}),"",${x})`:x;
};
for(let i=0;i<errorRows.length;i++){
  const x=errorRows[i],r=i+2,cross=x.direction==='Cross-road';
  errors.getRange(`A${r}:B${r}`).values=[[x.site_id,x.direction]];
  errors.getRange(`C${r}:F${r}`).formulas=[[
    `=${lookup(r,cross?'E':'L')}`,`=${lookup(r,cross?'F':'M')}`,
    `=${lookup(r,cross?'G':'N',true)}`,`=IF(${lookup(r,cross?'P':'Q')},1,0)`,
  ]];
  errors.getRange(`G${r}:L${r}`).formulas=[[
    `=D${r}-C${r}`,`=ABS(G${r})`,`=G${r}^2`,
    `=IF(ISNUMBER(E${r}),E${r}-C${r},"")`,`=IF(ISNUMBER(J${r}),ABS(J${r}),"")`,`=IF(ISNUMBER(J${r}),J${r}^2,"")`,
  ]];
  errors.getRange(`M${r}`).values=[[x.exclusion_reason||null]];
}

base(summary,'A1:N36');summary.tabColor=navy;
summary.getRange('A1:A36').format.columnWidth=3;
summary.getRange('B1:B36').format.columnWidth=18;
summary.getRange('C1:C36').format.columnWidth=44;
summary.getRange('D1:D36').format.columnWidth=10;
summary.getRange('E1:F36').format.columnWidth=14;
summary.getRange('G1:G36').format.columnWidth=3;
summary.getRange('H1:N36').format.columnWidth=14;
summary.getRange('B2').values=[['Pedestrian flow comparison']];summary.getRange('B2').format.font={name:font,size:15,bold:true};
summary.getRange('B3').values=[['Model OOF and existing estimates against corrected observed peak-hour counts']];
summary.getRange('B4').values=[['49 sites retained. Paired samples: 45 crossing; 43 along-road. Errors in pedestrians/hour.']];
summary.getRange('B6:F6').values=[['Direction','Method','N','MAE','RMSE']];header(summary,'B6:F6');
summary.getRange('B6:F6').format.rowHeight=28;
for(let i=0;i<4;i++){
  const m=payload.metrics[i],r=i+7,model=i%2===0,abs=model?'H':'K',sq=model?'I':'L';
  summary.getRange(`B${r}:C${r}`).values=[[m.direction,m.method]];
  summary.getRange(`D${r}`).formulas=[[`=COUNTIFS('Errors'!$B$2:$B$${errorEnd},B${r},'Errors'!$F$2:$F$${errorEnd},1)`]];
  summary.getRange(`E${r}`).formulas=[[`=IF(D${r}=0,"",SUMIFS('Errors'!$${abs}$2:$${abs}$${errorEnd},'Errors'!$B$2:$B$${errorEnd},B${r},'Errors'!$F$2:$F$${errorEnd},1)/D${r})`]];
  summary.getRange(`F${r}`).formulas=[[`=IF(D${r}=0,"",SQRT(SUMIFS('Errors'!$${sq}$2:$${sq}$${errorEnd},'Errors'!$B$2:$B$${errorEnd},B${r},'Errors'!$F$2:$F$${errorEnd},1)/D${r}))`]];
  summary.getRange(`B${r}:F${r}`).format.rowHeight=34;
  summary.getRange(`C${r}`).format.wrapText=true;
}
summary.getRange('D7:D10').setNumberFormat('0');summary.getRange('E7:F10').setNumberFormat('0.00');
summary.getRange('H6:K6').values=[['Direction','MAE reduction','RMSE reduction','Same paired sites']];header(summary,'H6:K6');summary.getRange('H6:K6').format.rowHeight=38;
summary.getRange('H7:K8').values=[['Cross-road',null,null,45],['Along-road',null,null,43]];
summary.getRange('I7:J8').formulas=[['=1-E7/E8','=1-F7/F8'],['=1-E9/E10','=1-F9/F10']];
summary.getRange('I7:J8').setNumberFormat('0.0%');
summary.getRange('H10').values=[['Reduction relative to Existing iRAP flow estimate (recoded).']];
summary.getRange('B12').values=[['Internal cross-validation; these results do not establish whole-network accuracy.']];
summary.getRange('B13').values=[['Along-road excludes 250341-01 and 260335-38 because coverage is not confirmed as both sides.']];
summary.getRange('H12').values=[['The reference is recoded and aggregated; it is not an official exact count.']];
summary.getRange('H13').values=[['The refitted correction-sensitivity analysis remains outstanding.']];

// Native XY charts store the frozen comparison snapshot as explicit XY values.
// Metric formulas remain live; plots are regenerated when the evaluation is rerun.
for(const [direction,startCell,endCell] of [['Cross-road','B15','F34'],['Along-road','H15','N34']]){
  const paired=errorRows.filter(r=>r.direction===direction&&r.eligible);
  const max=Math.ceil(Math.max(...paired.flatMap(r=>[r.observed,r.model_oof,r.existing_recoded]))/50)*50;
  const pc=direction==='Cross-road'?'O':'T', pe=direction==='Cross-road'?'R':'W';
  errors.getRange(`${pc}1:${pe}${paired.length+1}`).values=[
    ['Observed','Model (OOF)','Existing estimate (recoded)','1:1 reference'],
    ...paired.map(r=>[r.observed,r.model_oof,r.existing_recoded,r.observed]),
  ];
  const chart=summary.charts.add('scatter',errors.getRange(`${pc}1:${pe}${paired.length+1}`));
  chart.categories=paired.map(r=>String(r.observed));
  for(const [index,color] of [[0,blue],[1,orange],[2,'#8B959E']]){
    chart.series.items[index].fill=color;
    chart.series.items[index].line={fill:color,width:0};
  }
  chart.setPosition(startCell,endCell);
  chart.title=`${direction} (n = ${paired.length})`;
  chart.titleTextStyle.fontSize=14;chart.titleTextStyle.typeface=font;
  chart.hasLegend=true;chart.legend={position:'bottom',textStyle:{typeface:font,fontSize:10}};
  chart.xAxis={min:0,max,numberFormatCode:'0',numberFormatSourceLinked:false,textStyle:{typeface:font,fontSize:10}};
  chart.yAxis={min:0,max,numberFormatCode:'0',numberFormatSourceLinked:false,textStyle:{typeface:font,fontSize:10}};
  chart.xAxis.title.text='Observed (pedestrians/hour)';
  chart.yAxis.title.text='Estimated (pedestrians/hour)';
}

base(definitions,'A1:D40');
definitions.getRange('A1:D1').values=[['Technical field','Label','Unit','Meaning']];header(definitions,'A1:D1');
const meaning={
  existing_irap_cross_recoded_ped_per_h:'Client recoding of existing AusRAP categories; equal-weight mean of overlapping segments. Not an official exact count.',
  existing_irap_along_recoded_ped_per_h:'Client recoding; add the two sides within each segment, then average overlapping segments.',
  existing_ausrap_cross_category:'Blank for multiple source categories. The notes list the category set; numeric comparison can still be eligible.',
  observed_cross_category:'Project continuous rule: zero separately, positive upper bounds 5,25,50,100,200,300,400,500,900.',
  predicted_cross_category:'Same continuous rule as observed categories. Original numeric flow is not rounded.',
  existing_ausrap_cross_band:'Official category endpoints averaged over matched segments; a derived descriptive interval, not a confidence interval.',
  existing_ausrap_along_combined_band:'Sum the side endpoints within each segment, then average. No separate side columns are displayed.',
  cross_evaluation_eligible:'TRUE means both methods use this site in crossing summary metrics.',
  along_evaluation_eligible:'TRUE means both methods use this site in along-road summary metrics. Two coverage exceptions are FALSE.',
  pred_peak_cross_ped_per_h:'Saved road-grouped out-of-fold prediction, not a fitted value from the released model.',
  pred_peak_along_ped_per_h:'Saved road-grouped out-of-fold prediction, retaining existing numeric target coverage.',
};
definitions.getRange('A2:D20').values=fields.map(f=>[f[0],f[1],f[2],meaning[f[0]]??'See comparison protocol and source metadata below.']);
for(const [c,w]of[['A',47],['B',48],['C',22],['D',88]])definitions.getRange(`${c}1:${c}40`).format.columnWidth=w;
definitions.getRange('A1:D40').format.wrapText=true;definitions.getRange('A2:D20').format.rowHeight=52;
definitions.getRange('A23:B23').values=[['Source / convention','Details']];header(definitions,'A23:B23');
const sourceRows=[
  ['Protocol','irap_comparison_protocol_v1; positive_upper_bound_v1'],
  ['Observed counts','data/processed/model_dataset.xlsx, Model_Data: current corrected targets.'],
  ['OOF predictions','03_model_comparison_oof_predictions.csv; Model = Linear regression; Target = Cross-road / Along-road.'],
  ['Existing estimates','data/raw/Ped_iRAP_merged.csv; Ped_Peak_Cross and Ped_Peak_Along.'],
  ['Source categories and intervals','AusRAP Data - Words - MSDS.xlsx; source rows and fingerprints preserved in evidence/preflight_audit.json and evidence/manifest.json.'],
  ['Category dictionary','iRAP Star Rating and Investment Plan Manual, v1.5 (2024), pp. 26, 30–31.'],
  ['Official source','https://austroads.gov.au/__data/assets/pdf_file/0033/836295/iRAP_Star_Rating_and_Investment_Plan_Manual_English.pdf'],
  ['Continuous convention','0 has category 1; positives use inclusive upper bounds. 900 belongs to category 10; >900 to 11. This is a project convention.'],
  ['Client fixed recoding','1→0, 2→3, 3→15, 4→38, 5→75, 6→150, 7→250, 8→350, 9→450; no client recoding for 10/11.'],
  ['Missing data','Blank is unavailable, not zero. All 49 sites remain, including four without usable reference values.'],
  ['Mixed categories','24 of 45 matched sites have more than one crossing category; one original category is not invented.'],
  ['Model validation','Internal grouped cross-validation. Feature/model selection used the survey data; not external validation.'],
  ['Sensitivity status','Refitting after excluding corrected sites 250341-04 and 260335-38 has not been completed in this run.'],
  ['Workbook calculation','Summary formulas read Errors; Errors look up current Site_Comparison values by Site ID. XY plots store frozen comparison values; regenerate the workbook after editing inputs.'],
  ['Output scope','Separate OOF evaluation workbook. Production uses prediction_output_v5 (29 columns), released-model inference, and no accuracy metrics.'],
];
definitions.getRange(`A24:B${23+sourceRows.length}`).values=sourceRows;
definitions.getRange(`A24:B${23+sourceRows.length}`).format.rowHeight=76;
definitions.freezePanes.freezeRows(1);

wb.recalculate();
// Blank reference values and true zero values remain distinct after formulas.
for(let i=0;i<errorRows.length;i++){
  const values=errors.getRange(`C${i+2}:L${i+2}`).values[0], expected=errorRows[i];
  if(expected.existing_recoded===null){
    for(const j of [2,7,8,9]) if(values[j]!==''&&values[j]!==null)throw new Error(`Missing reference converted to a number at row ${i+2}`);
  }else if(Math.abs(values[2]-expected.existing_recoded)>1e-9||Math.abs(values[7]-expected.reference_error)>1e-9){
    throw new Error(`Reference calculation mismatch at row ${i+2}`);
  }
}
const metrics=summary.getRange('D7:F10').values;
for(let i=0;i<4;i++){
  const expected=payload.metrics[i];
  for(const [j,value]of[[0,expected.n],[1,expected.mae],[2,expected.rmse]]){
    if(typeof metrics[i][j]!=='number'||Math.abs(metrics[i][j]-value)>1e-9)throw new Error(`Metric mismatch ${i},${j}: ${metrics[i][j]} vs ${value}`);
  }
}
console.log('Recalculated metrics',JSON.stringify(metrics));
const scan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},summary:'Formula error scan'});
await fs.writeFile(`${out}/workbook_checks.json`,JSON.stringify({metrics,scan:scan.ndjson,chartCount:summary.charts.items.length},null,2));
console.log(scan.ndjson);
for(const [name,sheet,range]of[['summary_preview','Summary','B2:N34'],['crossing_preview','Site_Comparison','D1:K9'],['along_preview','Site_Comparison','L1:S9'],['definitions_preview','Definitions','A1:D7']]){
  const preview=await wb.render({sheetName:sheet,range,scale:1.25,format:'png'});
  await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await preview.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(`${out}/irap_comparison.xlsx`);
console.log(`Saved ${out}/irap_comparison.xlsx`);
