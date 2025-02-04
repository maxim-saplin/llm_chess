const data = `
Player,total_games,player_wins,opponent_wins,draws,player_wins_percent,player_draws_percent,total_moves,player_wrong_actions,player_wrong_moves,player_avg_material,opponent_avg_material,material_diff_player_llm_minus_opponent,wrong_actions_per_1000moves,wrong_moves_per_1000moves,mistakes_per_1000moves,average_moves,completion_tokens_black_per_move,moe_average_moves,moe_material_diff,moe_mistakes_per_1000moves,moe_completion_tokens_black_per_move
anthropic.claude-v3-5-sonnet-v1,60,4,8,48,6.666666666666667,80.0,11003,0,3,13.2,17.366666666666667,-4.166666666666667,0.0,1.6666666666666667,1.6666666666666667,183.38333333333333,80.42406616377352,10.151169172222898,3.0048638788338065,3.266666666666666,1.28149031781466
anthropic.claude-v3-5-sonnet-v2,60,2,5,53,3.3333333333333335,88.33333333333333,11292,0,8,10.816666666666666,13.833333333333334,-3.0166666666666666,0.0,2.9828722002635044,2.9828722002635044,188.2,90.8544987601842,9.393916954679366,2.559978723722791,4.561594266967543,1.142357874866914
anthropic.claude-v3-haiku,40,0,40,0,0.0,0.0,1334,7,4,36.725,37.15,-0.425,13.203463203463203,13.541666666666666,26.74512987012987,33.35,210.64017991004496,7.952752988906678,1.0732781200960555,30.686878575611857,81.16412124116572
anthropic.claude-v3-opus,30,0,5,25,0.0,83.33333333333334,4968,1,7,15.633333333333333,21.633333333333333,-6.0,1.8518518518518516,7.457634521313766,9.309486373165617,165.6,72.8623188405797,23.78205127121432,3.1590075554883033,12.310850869238884,4.832303432016992
deepseek-chat-v3,70,0,68,2,0.0,2.857142857142857,4043,10,180,32.17142857142857,30.52857142857143,1.6428571428571428,1.9779146503284433,96.34064766615487,98.31856231648331,57.75714285714286,246.92604501607718,11.860508178862721,1.424718024479006,20.819617008528166,8.419067135512611
deepseek-r1-distill-qwen-14b@q8_0,30,0,30,0,0.0,0.0,78,82,8,39.0,39.0,0.0,1175.0,116.66666666666667,1291.6666666666667,2.6,3073.0641025641025,0.3828824734899041,0.0,126.69910352977656,294.8332117524135
deepseek-r1-distill-qwen-32b@q4_k_m,30,0,30,0,0.0,0.0,110,73,7,39.0,38.96666666666667,0.03333333333333333,894.4444444444445,65.83333333333333,960.2777777777778,3.6666666666666665,2173.827272727273,0.8422855241630117,0.06533333333333333,174.45852569031015,409.7170270212998
deepseek-reasoner-r1,31,7,18,6,22.58064516129032,19.35483870967742,2845,9,44,21.93548387096774,10.806451612903226,11.129032258064516,6.105746600504369,46.825282688770564,52.93102928927493,91.7741935483871,4584.972583479789,22.88780015438446,3.6034642290753296,32.80503218251817,190.77372058839293
gemini-1.5-flash-001,30,0,20,10,0.0,33.33333333333333,2524,18,36,29.266666666666666,35.666666666666664,-6.4,114.57671957671957,229.15343915343914,343.73015873015873,84.13333333333334,19.914817749603802,33.52922259395211,3.1275403136959086,121.09496577679688,4.41176537691356
gemini-1.5-pro-preview-0409,40,0,37,3,0.0,7.5,2626,14,71,29.75,33.075,-3.325,4.7327303719316784,77.71717780731329,82.44990817924497,65.65,13.383472962680884,18.51170654145433,2.355334975359948,22.518459167327492,0.3541643238497577
gemini-2.0-flash-exp,30,0,28,2,0.0,6.666666666666667,2576,0,81,26.933333333333334,27.166666666666668,-0.23333333333333334,0.0,117.39474439973138,117.39474439973138,85.86666666666666,168.15023291925465,26.34577194255355,1.8811008597213612,46.898865011506324,16.07928337131627
gemini-2.0-flash-thinking-exp-01-21,33,0,33,0,0.0,0.0,1341,7,1,33.21212121212121,33.72727272727273,-0.5151515151515151,49.62982093663912,0.6184291898577613,50.24825012649688,40.63636363636363,17.76957494407159,8.571846527590305,1.8415713237103288,89.00386667429298,8.802824391986771
gemini-2.0-flash-thinking-exp-1219,30,0,30,0,0.0,0.0,70,89,1,39.0,39.0,0.0,1386.111111111111,5.555555555555555,1391.6666666666667,2.3333333333333335,724.5428571428571,0.3300286763344439,0.0,101.54969717418454,78.2856170519377
gemma-2-27b-it@q6_k_l,30,0,22,8,0.0,26.666666666666668,3268,8,52,25.466666666666665,26.333333333333332,-0.8666666666666667,3.831407649251797,48.07826143763394,51.90966908688574,108.93333333333334,55.04436964504284,25.251073216902363,2.669171283562778,24.91880310611584,2.7293574175775106
gemma-2-9b-it-8bit,30,0,26,4,0.0,13.333333333333334,2075,45,31,32.0,34.13333333333333,-2.1333333333333333,163.66922692296475,71.24054344481173,234.90977036777647,69.16666666666667,58.12433734939759,26.06307596164304,1.8045446926836475,135.3576928738708,4.686687185745504
gemma2-9b-it,35,0,35,0,0.0,0.0,516,83,22,38.714285714285715,38.31428571428572,0.4,414.8091421576605,61.745489264286256,476.55463142194674,14.742857142857142,20.217054263565892,5.266802758231758,0.5636118814762305,153.40236127109787,1.5078879385119421
gpt-35-turbo-0125,30,0,30,0,0.0,0.0,86,90,0,39.0,39.0,0.0,1285.0,0.0,1285.0,2.8666666666666667,82.02325581395348,0.6693575120421097,0.0,144.68382174888134,16.04020377336009
gpt-35-turbo-0301,30,0,30,0,0.0,0.0,68,90,0,39.0,39.0,0.0,1400.0,0.0,1400.0,2.2666666666666666,67.05882352941177,0.24744716530374364,0.0,92.79268698890385,14.051924570603521
gpt-35-turbo-0613,30,0,30,0,0.0,0.0,124,90,0,39.0,38.96666666666667,0.03333333333333333,1051.6666666666667,0.0,1051.6666666666667,4.133333333333334,93.62903225806451,1.0109755995251561,0.06533333333333333,188.72526363499827,19.57608849106176
gpt-35-turbo-1106,30,0,30,0,0.0,0.0,108,88,2,39.0,39.0,0.0,1130.2777777777778,8.88888888888889,1139.1666666666667,3.6,48.324074074074076,0.8694574341996607,0.0,176.0411046784201,8.190238149115658
gpt-4-turbo-2024-04-09,30,0,2,28,0.0,93.33333333333333,5786,0,0,15.433333333333334,20.8,-5.366666666666666,0.0,0.0,0.0,192.86666666666667,6.032837884548911,10.710544763647627,3.719412378917461,0.0,0.03095803458091743
gpt-4o-2024-05-13,60,0,12,48,0.0,80.0,11057,1,16,13.633333333333333,17.35,-3.716666666666667,0.08333333333333333,3.461510791480984,3.5448441248143174,184.28333333333333,31.334720086822827,9.43337606785952,1.9141124636605054,3.4918821253204784,0.8692038868007278
gpt-4o-2024-08-06,60,1,9,50,1.6666666666666667,83.33333333333334,11214,0,1,14.483333333333333,19.333333333333332,-4.85,0.0,0.15723270440251572,0.15723270440251572,186.9,7.70322810772249,8.050166925314263,2.5698508958923365,0.3081761006289308,0.3882429219180587
gpt-4o-2024-11-20,71,3,6,62,4.225352112676056,87.32394366197182,13470,1,1,11.901408450704226,19.901408450704224,-8.0,0.07042253521126761,0.07042253521126761,0.14084507042253522,189.71830985915494,50.575278396436524,7.5917787417310905,2.499408831512414,0.19380199803298997,0.2531172633271257
gpt-4o-mini-2024-07-18,30,0,12,18,0.0,60.0,4481,13,24,20.433333333333334,24.866666666666667,-4.433333333333334,4.701451970801815,31.083346306256523,35.784798277058336,149.36666666666667,108.21624637357732,25.1361939516602,3.093589178876671,27.63415379469353,8.09483715881323
granite-3.1-8b-instruct,30,0,30,0,0.0,0.0,126,47,12,38.96666666666667,39.0,-0.03333333333333333,447.5,91.66666666666667,539.1666666666666,4.2,469.12698412698415,0.8885465854319393,0.06533333333333333,175.53872863001527,204.83928800495804
grok-2-1212,49,2,32,15,4.081632653061225,30.612244897959183,5593,1,93,25.3265306122449,22.387755102040817,2.938775510204082,0.5102040816326531,32.28054641491559,32.79075049654825,114.14285714285714,66.22867870552476,19.00840515842049,2.5202645363797296,9.452880848247577,1.0367678864743854
internlm3-8b-instruct,30,0,30,0,0.0,0.0,108,15,39,39.0,39.0,0.0,166.66666666666666,412.5,579.1666666666666,3.6,1543.898148148148,0.6880085538094294,0.0,212.25208436669746,429.66933049762696
llama-2-7b-chat,30,0,30,0,0.0,0.0,64,88,2,39.0,39.0,0.0,1425.0,25.0,1450.0,2.1333333333333333,116.3125,0.1815765778944155,0.0,68.0912167104058,68.49300805930116
llama-3-70b-instruct-awq,30,0,15,15,0.0,50.0,4449,2,41,21.566666666666666,26.966666666666665,-5.4,0.606060606060606,22.27814337138526,22.884203977445868,148.3,41.60890087660148,22.339760638362048,3.0863249581219465,14.73482801691518,2.695118045011193
llama-3.1-8b-instant,60,0,60,0,0.0,0.0,1754,27,146,36.61666666666667,37.53333333333333,-0.9166666666666666,30.76101639149885,142.10738044440947,172.86839683590833,29.233333333333334,166.50513112884835,5.462544542044757,0.9808762560869637,34.00662041037932,69.2753200840037
llama-3.3-70b,42,0,38,4,0.0,9.523809523809524,2886,2,100,30.904761904761905,33.45238095238095,-2.5476190476190474,3.3068783068783065,107.34967736957964,110.65655567645794,68.71428571428571,102.98163548163548,20.992987447031435,1.745939462594872,39.03949591031765,5.654537714170008
llama3-8b-8192,60,0,60,0,0.0,0.0,902,104,66,38.2,38.68333333333333,-0.48333333333333334,206.94153142179456,89.71030395043553,296.6518353722301,15.033333333333333,57.019955654102,2.6672990154208023,0.5521978615883527,52.862007385599405,7.383641610185949
llama3.1-8b,90,0,87,3,0.0,3.3333333333333335,2436,44,188,37.2,37.833333333333336,-0.6333333333333333,35.03988017468409,126.64663826670215,161.68651844138626,27.066666666666666,162.1013957307061,4.595073421102033,0.8031280792068516,26.330820997178886,85.99671862172504
meta-llama-3.1-8b-instruct-fp16,30,0,30,0,0.0,0.0,830,19,61,36.733333333333334,37.0,-0.26666666666666666,72.35501567398119,135.4742208621519,207.8292365361331,27.666666666666668,71.86024096385542,8.127779599992463,1.7579402088176315,81.06662433363272,8.276308922639245
ministral-8b-instruct-2410,30,0,30,0,0.0,0.0,282,56,34,38.766666666666666,38.6,0.16666666666666666,453.517871017871,152.81204906204906,606.32992007992,9.4,72.11347517730496,2.4731626920098533,0.5645010681466399,187.55272893638383,12.893671903384732
mistral-nemo-12b-instruct-2407,30,0,30,0,0.0,0.0,202,79,11,38.766666666666666,38.666666666666664,0.1,733.9484126984127,42.5,776.4484126984127,6.733333333333333,47.698019801980195,1.83656043667174,0.5091145344570338,194.25541975034824,18.785382381523522
mistral-small-24b-instruct-2501@q4_k_m,42,0,42,0,0.0,0.0,854,3,123,37.404761904761905,37.73809523809524,-0.3333333333333333,4.8840048840048835,221.71666727807045,226.60067216207534,20.333333333333332,110.94847775175644,5.060551294453405,0.9199198739704155,39.781794364091574,4.957864158549713
mistral-small-instruct-2409,30,0,30,0,0.0,0.0,272,58,32,38.86666666666667,38.833333333333336,0.03333333333333333,365.49603174603175,127.91847041847042,493.41450216450215,9.066666666666666,88.24264705882354,1.9050094236550537,0.17539166898086328,136.37444332800882,21.22893063108001
o1-mini-2024-09-12,30,9,6,15,30.0,50.0,4282,2,8,17.666666666666668,7.033333333333333,10.633333333333333,0.9450830140485312,3.3492881937409673,4.294371207789498,142.73333333333332,1221.1361513311538,21.989890670688023,3.1596830822214796,4.291104179211649,79.49027019438729
o1-preview-2024-09-12,30,14,3,13,46.666666666666664,43.333333333333336,3744,4,10,17.8,4.033333333333333,13.766666666666667,2.9231524976205825,6.364050790877427,9.28720328849801,124.8,2660.071848290598,22.015672027094645,4.33577735498845,10.209580823090507,95.70634026690988
phi-4,30,0,30,0,0.0,0.0,232,44,46,39.0,39.0,0.0,264.8484848484849,232.67316017316017,497.52164502164504,7.733333333333333,333.5431034482759,1.6570861376020711,0.0,77.50941569812285,40.98349110044259
qwen-max-2025-01-25,60,0,2,58,0.0,96.66666666666667,11790,0,0,18.533333333333335,21.383333333333333,-2.85,0.0,0.0,0.0,196.5,6.06234096692112,4.9832298649576305,2.312460733519122,0.0,0.03740259781050197
qwen-plus-2025-01-25,33,0,30,3,0.0,9.090909090909092,2890,2,89,28.515151515151516,25.90909090909091,2.606060606060606,1.1784511784511784,64.85346359080525,66.03191476925642,87.57575757575758,440.41384083044983,21.2601060288111,2.7678388270035046,23.301275292440128,7.514843740905844
qwen-turbo-2024-11-01,33,0,33,0,0.0,0.0,674,4,95,38.0,38.333333333333336,-0.3333333333333333,10.267145135566189,220.3954220340021,230.6625671695683,20.424242424242426,192.3679525222552,4.76985475846972,1.0470024553047341,60.2042865302614,26.099217852600777
qwen2.5-14b-instruct-1m,42,0,42,0,0.0,0.0,312,48,49,38.857142857142854,38.95238095238095,-0.09523809523809523,241.01473922902494,174.8015873015873,415.81632653061223,7.428571428571429,235.26602564102564,1.6807586362996725,0.1743062128168651,101.60180969161259,84.93704953378911
qwen2.5-14b-instruct@q8_0,30,0,30,0,0.0,0.0,398,29,59,38.56666666666667,38.4,0.16666666666666666,156.93121693121694,212.67376142376142,369.60497835497836,13.266666666666667,150.63065326633165,3.58823002291074,0.6379452167834305,109.70238708464787,18.310920002059007
qwen2.5-72b-instruct,30,0,28,2,0.0,6.666666666666667,1923,10,71,30.666666666666668,32.733333333333334,-2.066666666666667,8.232851372597288,81.14434750949682,89.37719888209412,64.1,219.46541861674467,18.287301879254592,2.1095896497711246,34.98270454165298,10.325241284331659
qwen2.5-7b-instruct-1m,42,0,42,0,0.0,0.0,406,33,93,38.73809523809524,38.714285714285715,0.023809523809523808,180.37732769875626,403.05560841275127,583.4329361115075,9.666666666666666,140.79064039408868,2.1119425548564403,0.1946075196925011,147.80333527597642,16.12567238726695
qwq-32b-preview@q4_k_m,30,0,30,0,0.0,0.0,239,44,17,38.86666666666667,38.96666666666667,-0.1,308.6381673881674,97.35569985569985,405.9938672438672,7.966666666666667,2908.0,1.734041040316496,0.21736435854991518,157.30378191102815,407.07021980501514
sky-t1-32b-preview,30,0,30,0,0.0,0.0,415,9,59,38.766666666666666,38.8,-0.03333333333333333,24.57070707070707,185.1043159738812,209.67502304458827,13.833333333333334,1216.1590361445783,3.3279335113458464,0.34507228405951934,60.69321478449664,483.6306332021484
Stockfish chess engine (as Black),1000,1000,0,0,100.000,0.000,32368,0,0,38.21,21.01,17.21,0.53164,0.00,0.00,32.37,-
Random Player (as White),1000,105,0,895,10.5,89.5,190073,0,0,10.56,11.08,-0.52,-0.00274,0.00,0.00,190.07,-
Random Player (as Black),1000,0,105,895,0.000,89.5,190073,0,0,11.08,10.56,0.52,0.00274,0.00,0.00,190.07,-
    `
const csvIndices = {
    player: 0,
    total_games: 1,
    player_wins: 2,
    losses: 3,
    draws: 4,
    player_wins_percent: 5,
    player_draws_percent: 6,
    total_moves: 7,
    player_wrong_actions: 8,
    player_wrong_moves: 9,
    player_avg_material: 10,
    opponent_avg_material: 11,
    material_diff: 12,
    wrong_actions_per_1000moves: 13,
    wrong_moves_per_1000moves: 14,
    mistakes_per_1000moves: 15,
    average_moves: 16,
    completion_tokens_black_per_move: 17,
    moe_average_moves: 18,
    moe_material_diff: 19,
    moe_mistakes_per_1000moves: 20,
    moe_completion_tokens_black_per_move: 21,
};

let currentSortOrder = {};

const SPECIAL_ROWS = {
    STOCKFISH: "Stockfish chess engine (as Black)",
    RANDOM_WHITE: "Random Player (as White)",
    RANDOM_BLACK: "Random Player (as Black)"
};

document.addEventListener('DOMContentLoaded', () => {
    buildTable();
    fetchAndAnimateBoard();
});

function showPane(paneId) {
    document.getElementById('leaderboard').style.display = paneId === 'leaderboard' ? 'block' : 'none';
    document.getElementById('how-it-works').style.display = paneId === 'how-it-works' ? 'block' : 'none';
    document.getElementById('considerations').style.display = paneId === 'considerations' ? 'block' : 'none';
    document.querySelectorAll('.button-container button').forEach(button => {
        button.classList.remove('selected');
    });
    document.querySelector(`.button-container button[onclick="showPane('${paneId}')"]`).classList.add('selected');

    // Simulate a page view event in Google Analytics
    gtag('event', 'page_view', {
        'page_title': document.title + ' - ' + paneId,
        'page_path': '/' + paneId
    });
}

function buildTable() {
    const lines = data.trim().split('\n');
    // const header = lines[0].split(',');
    const rows = lines.slice(1).map(row => row.split(','));

    // Separate the rows that should always be at the bottom
    const bottomRows = [];
    const otherRows = rows.filter(columns => {
        const player = columns[csvIndices.player];
        if (player === SPECIAL_ROWS.STOCKFISH ||
            player === SPECIAL_ROWS.RANDOM_WHITE ||
            player === SPECIAL_ROWS.RANDOM_BLACK) {
            bottomRows.push(columns);
            return false;
        }
        return true;
    });

    // Sort the remaining rows by "Wins", "Draws", and then "Mistakes" in descending order
    otherRows.sort((a, b) => {
        const winsA = parseFloat(a[csvIndices.player_wins_percent]);
        const winsB = parseFloat(b[csvIndices.player_wins_percent]);
        const drawsA = parseFloat(a[csvIndices.player_draws_percent]);
        const drawsB = parseFloat(b[csvIndices.player_draws_percent]);
        const mistakesA = parseFloat(a[csvIndices.mistakes_per_1000moves]);
        const mistakesB = parseFloat(b[csvIndices.mistakes_per_1000moves]);

        // Hierarchical sorting: Wins DESC, Draws DESC, Mistakes ASC
        return winsB - winsA || drawsB - drawsA || mistakesA - mistakesB;
    });

    const tbody = document.querySelector('#leaderboard tbody');
    [...otherRows, ...bottomRows].forEach((columns, index) => {
        const isBottomRow = bottomRows.includes(columns); // Check if the row is a bottom row
        const player = columns[csvIndices.player];
        const player_wins_percent = parseFloat(columns[csvIndices.player_wins_percent]);
        const player_draws_percent = parseFloat(columns[csvIndices.player_draws_percent]);
        const wrong_actions_per_1000moves = parseFloat(columns[csvIndices.wrong_actions_per_1000moves]);
        const wrong_moves_per_1000moves = parseFloat(columns[csvIndices.wrong_moves_per_1000moves]);
        const mistakes = wrong_actions_per_1000moves + wrong_moves_per_1000moves;
        const tokens = parseFloat(columns[csvIndices.completion_tokens_black_per_move]);

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${isBottomRow ? '' : index + 1}</td> <!-- Empty rank for bottom rows -->
            <td>${player}</td> <!-- Player first -->
            <td>${player_wins_percent.toFixed(2)}%</td>
            <td>${player_draws_percent.toFixed(2)}%</td>
            <td>${mistakes.toFixed(2)}</td>
            <td>${tokens.toFixed(2)}</td>
        `;
        tbody.appendChild(tr);

        // Add event listeners for hover and tap
        tr.addEventListener('mouseenter', () => showPopup(tr, columns));
        tr.addEventListener('mouseleave', hidePopup);
        tr.addEventListener('click', () => showPopup(tr, columns));
    });

    // Add a non-breaking space to all headers
    document.querySelectorAll('#leaderboard th').forEach((headerCell) => {
        const baseText = headerCell.textContent.trim();
        headerCell.innerHTML = `${baseText}&nbsp;&nbsp;`;
    });

    document.querySelectorAll('#leaderboard th').forEach((headerCell, index) => {
        headerCell.addEventListener('click', () => {
            sortTable(index);
        });
    });
}

function sortTable(columnIndex) {
    const table = document.querySelector('#leaderboard tbody');
    const rows = Array.from(table.rows);
    const isNumericColumn = columnIndex !== 0; // Assuming first column is not numeric

    // Determine the current sort order for the column
    const currentOrder = currentSortOrder[columnIndex] || 'asc';
    const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    currentSortOrder[columnIndex] = newOrder;

    // Separate the rows that should always be at the bottom
    const bottomRows = [];
    const otherRows = rows.filter(row => {
        const player = row.cells[1].textContent.trim(); // Use the Player column to identify special rows
        if (player === SPECIAL_ROWS.STOCKFISH ||
            player === SPECIAL_ROWS.RANDOM_WHITE ||
            player === SPECIAL_ROWS.RANDOM_BLACK) {
            bottomRows.push(row);
            return false;
        }
        return true;
    });

    // Sort only the other rows
    otherRows.sort((a, b) => {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();

        const comparison = isNumericColumn
            ? parseFloat(aText) - parseFloat(bText)
            : aText.localeCompare(bText);

        return newOrder === 'asc' ? comparison : -comparison;
    });

    // Append sorted rows and then the bottom rows
    [...otherRows, ...bottomRows].forEach(row => table.appendChild(row));

    // Clear all sort indicators
    document.querySelectorAll('#leaderboard th').forEach((headerCell) => {
        const baseText = headerCell.textContent.replace(/[▲▼]/g, '').trim();
        headerCell.innerHTML = `${baseText}&nbsp;&nbsp;`;
    });

    // Update header text with sorting indicator for the sorted column
    const sortedHeaderCell = document.querySelectorAll('#leaderboard th')[columnIndex];
    const baseText = sortedHeaderCell.textContent.replace(/[▲▼]/g, '').trim();
    const indicator = currentSortOrder[columnIndex] === 'asc' ? '▲' : '▼';
    sortedHeaderCell.innerHTML = `${baseText}${indicator ? '&nbsp;' + indicator : '&nbsp;&nbsp;'}`;
}

function fetchAndAnimateBoard() {
    fetch('moves.txt')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(data => {
            const boardStates = data.trim().split('-\n');
            let currentIndex = 0;

            let interval = 1000; // Initial interval in milliseconds
            let resetGameInterval = 7000;

            function animateBoard() {
                document.querySelector('pre.board').textContent = boardStates[currentIndex].trim();
                document.querySelector('div.game-over').style.display = 'none';
                currentIndex = (currentIndex + 1) % boardStates.length;

                if (currentIndex === 0) {
                    document.querySelector('div.game-over').style.display = 'block';
                    currentIndex = 0;
                    setTimeout(animateBoard, resetGameInterval);
                } else {
                    // Decrease the interval progressively
                    interval = Math.max(50, interval - 25); // Decrease by 25ms, but not less than 50ms
                    setTimeout(animateBoard, interval);
                }
            }

            animateBoard(); // Start the animation
        })
        .catch(error => {
            console.error('Error fetching moves.txt:', error);
        });
}

function showPopup(row, columns) {
    const popup = document.getElementById('popup');
    const totalGames = columns[csvIndices.total_games];
    const wins = columns[csvIndices.player_wins];
    const losses = columns[csvIndices.losses];
    const draws = columns[csvIndices.draws];
    const averageMoves = columns[csvIndices.average_moves];
    const materialDiff = columns[csvIndices.material_diff];

    const moeAverageMoves = columns[csvIndices.moe_average_moves];
    const moeMaterialDiff = columns[csvIndices.moe_material_diff];
    // const moeMistakesPer1000Moves = columns[csvIndices.moe_mistakes_per_1000moves];
    // const moeCompletionTokensBlackPerMove = columns[csvIndices.moe_completion_tokens_black_per_move];

    document.getElementById('total-games').textContent = `Games: ${parseInt(totalGames)}`;
    document.getElementById('wins').textContent = `Wins: ${parseInt(wins)} | ${((parseInt(wins) / parseInt(totalGames)) * 100).toFixed(2)}%`;
    document.getElementById('losses').textContent = `Losses: ${parseInt(losses)} | ${((parseInt(losses) / parseInt(totalGames)) * 100).toFixed(2)}%`;
    const winsMinusLossesPercent = ((parseInt(wins) - parseInt(losses)) / parseInt(totalGames) * 100).toFixed(2);
    document.getElementById('wins_minus_losses').textContent = `Wins - Losses: ${winsMinusLossesPercent}%`;
    document.getElementById('draws').textContent = `Draws: ${parseInt(draws)} | ${((parseInt(draws) / parseInt(totalGames)) * 100).toFixed(2)}%`;
    document.getElementById('average-moves').textContent = `Average Moves: ${parseFloat(averageMoves).toFixed(2)} ± ${parseFloat(moeAverageMoves).toFixed(2)}`;
    document.getElementById('material-diff').textContent = `Material Diff: ${parseFloat(materialDiff).toFixed(2)} ± ${parseFloat(moeMaterialDiff).toFixed(2)}`;

    const rect = row.getBoundingClientRect();
    if (window.innerWidth < 1200) {
        popup.style.top = `${rect.bottom + window.scrollY}px`;                
        popup.style.right = `${rect.left + window.scrollX}px`;
        popup.style.left = '';
    }
    else {
        popup.style.top = `${rect.top + window.scrollY}px`;
        popup.style.left = `${rect.right + window.scrollX}px`;
        popup.style.right = '';
    }
    popup.style.display = 'block';
}

function hidePopup() {
    const popup = document.getElementById('popup');
    popup.style.display = 'none';
}

function toggleSnippet(button) {
    const snippet = button.nextElementSibling; // Get the <pre> element
    if (snippet.style.display === "none") {
        snippet.style.display = "block";
        button.textContent = "Hide Snippet";
    } else {
        snippet.style.display = "none";
        button.textContent = "Show Snippet";
    }
}
