const data = `
anthropic.claude-v3-5-sonnet,30,0,8,22,0.0,73.33333333333333,5148,0,12,15.8,22.5,-6.7,-36.953723217813106,0.0,14.657738095238095,171.6,81.07478632478633
anthropic.claude-v3-5-sonnet-v1,60,4,8,48,6.666666666666667,80.0,11003,0,3,13.2,17.366666666666667,-4.166666666666667,-19.325398324516605,0.0,1.6666666666666665,183.38333333333333,80.42406616377352
anthropic.claude-v3-5-sonnet-v2,60,2,5,53,3.3333333333333335,88.33333333333333,11292,0,8,10.816666666666666,13.833333333333334,-3.0166666666666666,-5.1134194118105745,0.0,2.9828722002635044,188.2,90.8544987601842
anthropic.claude-v3-haiku,40,0,40,0,0.0,0.0,1334,7,4,36.725,37.15,-0.425,-11.710852516809853,13.203463203463201,13.541666666666664,33.35,210.64017991004496
anthropic.claude-v3-opus,30,0,5,25,0.0,83.33333333333334,4968,1,7,15.633333333333333,21.633333333333333,-6.0,-33.49803552340468,1.8518518518518516,7.457634521313766,165.6,72.8623188405797
deepseek-chat-v3,70,0,68,2,0.0,2.857142857142857,4043,10,180,32.17142857142857,30.52857142857143,1.6428571428571428,35.272572014318335,1.9779146503284433,96.34064766615487,57.75714285714286,246.92604501607718
deepseek-r1-distill-qwen-14b@q8_0,30,0,30,0,0.0,0.0,78,82,8,39.0,39.0,0.0,0.0,1175.0,116.66666666666666,2.6,3073.0641025641025
deepseek-r1-distill-qwen-32b@q4_k_m,30,0,30,0,0.0,0.0,110,73,7,39.0,38.96666666666667,0.03333333333333333,3.333333333333333,894.4444444444445,65.83333333333333,3.6666666666666665,2173.827272727273
deepseek-reasoner-r1,31,7,18,6,22.58064516129032,19.35483870967742,2845,9,44,21.93548387096774,10.806451612903226,11.129032258064516,170.38444469706076,6.10574660050437,46.825282688770564,91.7741935483871,4584.972583479789
gemini-1.5-flash-001,30,0,20,10,0.0,33.33333333333333,2524,18,36,29.266666666666666,35.666666666666664,-6.4,-33.14049391468746,114.57671957671957,229.15343915343914,84.13333333333334,19.914817749603802
gemini-1.5-pro-preview-0409,40,0,37,3,0.0,7.5,2626,14,71,29.75,33.075,-3.325,-38.3699709622505,4.7327303719316784,77.71717780731329,65.65,13.383472962680884
gemini-2.0-flash-exp,30,0,28,2,0.0,6.666666666666667,2576,0,81,26.933333333333334,27.166666666666668,-0.23333333333333334,-12.193564485896013,0.0,117.39474439973138,85.86666666666666,168.15023291925465
gemini-2.0-flash-thinking-exp-01-21,33,0,33,0,0.0,0.0,1341,7,1,33.21212121212121,33.72727272727273,-0.5151515151515151,-7.6864192192695455,49.62982093663911,0.6184291898577613,40.63636363636363,17.76957494407159
gemini-2.0-flash-thinking-exp-1219,30,0,30,0,0.0,0.0,70,89,1,39.0,39.0,0.0,0.0,1386.111111111111,5.5555555555555545,2.3333333333333335,724.5428571428571
gemma-2-27b-it@q6_k_l,30,0,22,8,0.0,26.666666666666668,3268,8,52,25.466666666666665,26.333333333333332,-0.8666666666666667,13.392604995286117,3.8314076492517968,48.07826143763394,108.93333333333334,55.04436964504284
gemma-2-9b-it-8bit,30,0,26,4,0.0,13.333333333333334,2075,45,31,32.0,34.13333333333333,-2.1333333333333333,-30.559760306903236,163.66922692296473,71.24054344481173,69.16666666666667,58.12433734939759
gemma2-9b-it,35,0,35,0,0.0,0.0,516,83,22,38.714285714285715,38.31428571428572,0.4,11.613037559521416,414.8091421576605,61.74548926428625,14.742857142857142,20.217054263565892
gpt-35-turbo-0125,30,0,30,0,0.0,0.0,86,90,0,39.0,39.0,0.0,0.0,1285.0,0.0,2.8666666666666667,82.02325581395348
gpt-35-turbo-0301,30,0,30,0,0.0,0.0,68,90,0,39.0,39.0,0.0,0.0,1400.0,0.0,2.2666666666666666,67.05882352941177
gpt-35-turbo-0613,30,0,30,0,0.0,0.0,124,90,0,39.0,38.96666666666667,0.03333333333333333,2.7777777777777772,1051.6666666666667,0.0,4.133333333333334,93.62903225806451
gpt-35-turbo-1106,30,0,30,0,0.0,0.0,108,88,2,39.0,39.0,0.0,0.0,1130.2777777777778,8.88888888888889,3.6,48.324074074074076
gpt-4-turbo-2024-04-09,30,0,2,28,0.0,93.33333333333333,5786,0,0,15.433333333333334,20.8,-5.366666666666666,-30.62647754137116,0.0,0.0,192.86666666666667,6.032837884548911
gpt-4o-2024-05-13,60,0,12,48,0.0,80.0,11057,1,16,13.633333333333333,17.35,-3.716666666666667,-15.277597049390701,0.08333333333333333,3.461510791480984,184.28333333333333,31.334720086822827
gpt-4o-2024-08-06,60,1,9,50,1.6666666666666667,83.33333333333334,11214,0,1,14.483333333333333,19.333333333333332,-4.85,-32.06579503621741,0.0,0.15723270440251572,186.9,7.70322810772249
gpt-4o-2024-11-20,71,3,6,62,4.225352112676056,87.32394366197182,13470,1,1,11.901408450704226,19.901408450704224,-8.0,-41.770473664269865,0.07042253521126761,0.07042253521126761,189.71830985915494,50.575278396436524
gpt-4o-mini-2024-07-18,30,0,12,18,0.0,60.0,4481,13,24,20.433333333333334,24.866666666666667,-4.433333333333334,-38.65782480051881,4.701451970801816,31.083346306256523,149.36666666666667,108.21624637357732
granite-3.1-8b-instruct,30,0,30,0,0.0,0.0,126,47,12,38.96666666666667,39.0,-0.03333333333333333,-4.166666666666667,447.5,91.66666666666666,4.2,469.12698412698415
grok-2-1212,49,2,32,15,4.081632653061225,30.612244897959183,5593,1,93,25.3265306122449,22.387755102040817,2.938775510204082,42.245054095055764,0.5102040816326531,32.28054641491559,114.14285714285714,66.22867870552476
internlm3-8b-instruct,30,0,30,0,0.0,0.0,108,15,39,39.0,39.0,0.0,0.0,166.66666666666669,412.5,3.6,1543.898148148148
llama-2-7b-chat,30,0,30,0,0.0,0.0,64,88,2,39.0,39.0,0.0,0.0,1425.0,25.0,2.1333333333333333,116.3125
llama-3-70b-instruct-awq,30,0,15,15,0.0,50.0,4449,2,41,21.566666666666666,26.966666666666665,-5.4,-21.856163100745917,0.606060606060606,22.27814337138526,148.3,41.60890087660148
llama-3.1-8b-instant,60,0,60,0,0.0,0.0,1754,27,146,36.61666666666667,37.53333333333333,-0.9166666666666666,-29.803101898153308,30.761016391498845,142.10738044440947,29.233333333333334,166.50513112884835
llama-3.3-70b,42,0,38,4,0.0,9.523809523809524,2886,2,100,30.904761904761905,33.45238095238095,-2.5476190476190474,-12.651372376559515,3.3068783068783065,107.34967736957964,68.71428571428571,102.98163548163548
llama3-8b-8192,60,0,60,0,0.0,0.0,902,104,66,38.2,38.68333333333333,-0.48333333333333334,-14.169665566917889,206.9415314217946,89.71030395043553,15.033333333333333,57.019955654102
llama3.1-8b,90,0,87,3,0.0,3.3333333333333335,2436,44,188,37.2,37.833333333333336,-0.6333333333333333,-15.745408923494072,35.03988017468409,126.64663826670215,27.066666666666666,162.1013957307061
meta-llama-3.1-8b-instruct-fp16,30,0,30,0,0.0,0.0,830,19,61,36.733333333333334,37.0,-0.26666666666666666,4.630161770966371,72.35501567398119,135.4742208621519,27.666666666666668,71.86024096385542
ministral-8b-instruct-2410,30,0,30,0,0.0,0.0,282,56,34,38.766666666666666,38.6,0.16666666666666666,13.888888888888886,453.517871017871,152.81204906204906,9.4,72.11347517730496
mistral-nemo-12b-instruct-2407,30,0,30,0,0.0,0.0,202,79,11,38.766666666666666,38.666666666666664,0.1,13.75,733.9484126984127,42.5,6.733333333333333,47.698019801980195
mistral-small-24b-instruct-2501@q4_k_m,42,0,42,0,0.0,0.0,854,3,123,37.404761904761905,37.73809523809524,-0.3333333333333333,-4.2997843174401345,4.8840048840048835,221.71666727807047,20.333333333333332,110.94847775175644
mistral-small-instruct-2409,30,0,30,0,0.0,0.0,272,58,32,38.86666666666667,38.833333333333336,0.03333333333333333,4.318181818181818,365.4960317460318,127.91847041847042,9.066666666666666,88.24264705882354
o1-mini-2024-09-12,30,9,6,15,30.0,50.0,4282,2,8,17.666666666666668,7.033333333333333,10.633333333333333,94.87098362233894,0.9450830140485312,3.3492881937409673,142.73333333333332,1221.1361513311538
o1-preview-2024-09-12,30,14,3,13,46.666666666666664,43.333333333333336,3744,4,10,17.8,4.033333333333333,13.766666666666667,182.50560050089678,2.9231524976205825,6.364050790877428,124.8,2660.071848290598
phi-4,30,0,30,0,0.0,0.0,232,44,46,39.0,39.0,0.0,0.0,264.8484848484849,232.67316017316017,7.733333333333333,333.5431034482759
qwen-max-2025-01-25,60,0,2,58,0.0,96.66666666666667,11790,0,0,18.533333333333335,21.383333333333333,-2.85,-16.695668001456134,0.0,0.0,196.5,6.06234096692112
qwen-plus-2025-01-25,33,0,30,3,0.0,9.090909090909092,2890,2,89,28.515151515151516,25.90909090909091,2.606060606060606,50.09424512759104,1.1784511784511784,64.85346359080525,87.57575757575758,440.41384083044983
qwen-turbo-2024-11-01,33,0,33,0,0.0,0.0,674,4,95,38.0,38.333333333333336,-0.3333333333333333,-21.689522561731494,10.267145135566189,220.39542203400208,20.424242424242426,192.3679525222552
qwen2.5-14b-instruct@q8_0,30,0,30,0,0.0,0.0,398,29,59,38.56666666666667,38.4,0.16666666666666666,3.192640692640695,156.93121693121694,212.67376142376145,13.266666666666667,150.63065326633165
qwen2.5-72b-instruct,30,0,28,2,0.0,6.666666666666667,1923,10,71,30.666666666666668,32.733333333333334,-2.066666666666667,-23.86190778620155,8.232851372597288,81.14434750949682,64.1,219.46541861674467
qwen2.5-7b-instruct-1m,42,0,42,0,0.0,0.0,406,33,93,38.73809523809524,38.714285714285715,0.023809523809523808,3.9694102194102188,180.3773276987563,403.0556084127512,9.666666666666666,140.79064039408868
qwq-32b-preview@q4_k_m,30,0,30,0,0.0,0.0,239,44,17,38.86666666666667,38.96666666666667,-0.1,-13.068181818181818,308.6381673881674,97.35569985569984,7.966666666666667,2908.0
sky-t1-32b-preview,30,0,30,0,0.0,0.0,415,9,59,38.766666666666666,38.8,-0.03333333333333333,-0.8086036346905914,24.570707070707073,185.1043159738812,13.833333333333334,1216.1590361445783
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
    wrong_actions_per_1000moves: 14,
    wrong_moves_per_1000moves: 15,
    completion_tokens_black_per_move: 17,
    average_moves: 16,
    material_diff: 12,

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
    const header = lines[0].split(',');
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
        const mistakesA = parseFloat(a[csvIndices.wrong_actions_per_1000moves]) + parseFloat(a[csvIndices.wrong_moves_per_1000moves]);
        const mistakesB = parseFloat(b[csvIndices.wrong_actions_per_1000moves]) + parseFloat(b[csvIndices.wrong_moves_per_1000moves]);

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
    const wins = columns[csvIndices.player_wins]; // Retrieve wins
    const losses = columns[csvIndices.losses];    // Retrieve losses
    const draws = columns[csvIndices.draws];      // Retrieve draws
    const averageMoves = columns[csvIndices.average_moves]; // Retrieve average moves
    const materialDiff = columns[csvIndices.material_diff]; // Retrieve material difference

    document.getElementById('total-games').textContent = `Games: ${parseInt(totalGames)}`;
    document.getElementById('wins').textContent = `Wins: ${parseInt(wins)} | ${((parseInt(wins) / parseInt(totalGames)) * 100).toFixed(2)}%`;
    document.getElementById('losses').textContent = `Losses: ${parseInt(losses)} | ${((parseInt(losses) / parseInt(totalGames)) * 100).toFixed(2)}%`;
    const winsMinusLossesPercent = ((parseInt(wins) - parseInt(losses)) / parseInt(totalGames) * 100).toFixed(2);
    document.getElementById('wins_minus_losses').textContent = `Wins - Losses: ${winsMinusLossesPercent}%`;
    document.getElementById('draws').textContent = `Draws: ${parseInt(draws)} | ${((parseInt(draws) / parseInt(totalGames)) * 100).toFixed(2)}%`;
    document.getElementById('average-moves').textContent = `Average Moves: ${parseFloat(averageMoves).toFixed(2)}`;
    document.getElementById('material-diff').textContent = `Material Diff: ${parseFloat(materialDiff).toFixed(2)}`;

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
