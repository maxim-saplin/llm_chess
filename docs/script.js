const Screen = {
    LEADERBOARD_NEW: 'leaderboard_new',
    LEADERBOARD_OLD: 'leaderboard_old',
    HOW_IT_WORKS: 'how_it_works',
    NOTES: 'notes'
};

const SPECIAL_ROWS = {
    STOCKFISH: "Stockfish chess engine (as Black)",
    RANDOM_WHITE: "Random Player (as White)",
    RANDOM_BLACK: "Random Player (as Black)"
};

let sortOrderState = {
    [Screen.LEADERBOARD_NEW]: {},
    [Screen.LEADERBOARD_OLD]: {}
};

let currentScreen = Screen.LEADERBOARD_NEW;

const csvIndices = {
    player: 0,
    total_games: 1,
    player_wins: 2,
    opponent_wins: 3,
    draws: 4,
    player_wins_percent: 5,
    player_draws_percent: 6,
    average_moves: 7,
    moe_average_moves: 8,
    total_moves: 9,
    player_wrong_actions: 10,
    player_wrong_moves: 11,
    wrong_actions_per_1000moves: 12,
    wrong_moves_per_1000moves: 13,
    mistakes_per_1000moves: 14,
    moe_mistakes_per_1000moves: 15,
    player_avg_material: 16,
    opponent_avg_material: 17,
    material_diff_player_llm_minus_opponent: 18,
    moe_material_diff_llm_minus_rand: 19,
    completion_tokens_black_per_move: 20,
    moe_completion_tokens_black_per_move: 21,
    std_dev_black_llm_win_rate: 22,
    moe_black_llm_win_rate: 23,
    std_dev_draw_rate: 24,
    moe_draw_rate: 25,
    std_dev_black_llm_loss_rate: 26,
    moe_black_llm_loss_rate: 27,
};

document.addEventListener('DOMContentLoaded', () => {
    fetchAndAnimateBoard();
    
    // Select Leaderboard by default
    showPane(Screen.LEADERBOARD_NEW);
    
    // Initialize markdown rendering
    MinimalMD.render('considerations');
});

// Define table configs for NEW and OLD leaderboards
const tableConfigs = {
    [Screen.LEADERBOARD_NEW]: {
        columns: [
            { title: '#', tooltip: 'Rank of the model', getValue: (cols, idx) => idx + 1, isNumeric: true, isRankColumn: true },
            { title: 'Player', tooltip: 'Model playing against Random Player', getValue: (cols) => cols[csvIndices.player], isNumeric: false },
            { title: 'Wins-Losses', tooltip: 'Difference between wins & losses', getValue: (cols) =>
                ((parseInt(cols[csvIndices.player_wins]) -
                  parseInt(cols[csvIndices.opponent_wins])) /
                  parseInt(cols[csvIndices.total_games]) * 100).toFixed(2) + '%', 
              isNumeric: true 
            },
            { title: 'Avg Moves', getValue: (cols) => parseFloat(cols[csvIndices.average_moves]).toFixed(1), isNumeric: true },
            { title: 'Mistakes', getValue: (cols) => parseFloat(cols[csvIndices.mistakes_per_1000moves]).toFixed(2), isNumeric: true },
            { title: 'Tokens', getValue: (cols) => parseFloat(cols[csvIndices.completion_tokens_black_per_move]).toFixed(2), isNumeric: true }
        ],
        defaultSortCompare: (colsA, colsB) => {
            const winsMinusLossesA = parseFloat(colsA[csvIndices.player_wins_percent]) - parseFloat(colsA[csvIndices.opponent_wins_percent]);
            const winsMinusLossesB = parseFloat(colsB[csvIndices.player_wins_percent]) - parseFloat(colsB[csvIndices.opponent_wins_percent]);
            const avgMovesA = parseFloat(colsA[csvIndices.average_moves]);
            const avgMovesB = parseFloat(colsB[csvIndices.average_moves]);
            const mistakesA = parseFloat(colsA[csvIndices.mistakes_per_1000moves]);
            const mistakesB = parseFloat(colsB[csvIndices.mistakes_per_1000moves]);
            return (winsMinusLossesB - winsMinusLossesA) || (avgMovesB - avgMovesA) || (mistakesA - mistakesB);
        }
    },
    [Screen.LEADERBOARD_OLD]: {
        columns: [
            { title: '#', tooltip: 'Rank of the model', getValue: (cols, idx) => idx + 1, isNumeric: true, isRankColumn: true },
            { title: 'Player', tooltip: 'Model playing against Random Player', getValue: (cols) => cols[csvIndices.player], isNumeric: false },
            { title: 'Wins', tooltip: 'Wins as a percentage of all games', getValue: (cols) =>
                ((parseInt(cols[csvIndices.player_wins]) / parseInt(cols[csvIndices.total_games])) * 100).toFixed(2) + '%',
              isNumeric: true
            },
            { title: 'Draws', getValue: (cols) => parseFloat(cols[csvIndices.player_draws_percent]).toFixed(2) + '%', isNumeric: true },
            { title: 'Mistakes', getValue: (cols) => parseFloat(cols[csvIndices.mistakes_per_1000moves]).toFixed(2), isNumeric: true },
            { title: 'Tokens', getValue: (cols) => parseFloat(cols[csvIndices.completion_tokens_black_per_move]).toFixed(2), isNumeric: true }
        ],
        // Sorting priority for OLD leaderboard: Wins DESC, Draws DESC, Mistakes ASC
        defaultSortCompare: (colsA, colsB) => {
            const winsA = parseFloat(colsA[csvIndices.player_wins]) / parseFloat(colsA[csvIndices.total_games]) * 100;
            const winsB = parseFloat(colsB[csvIndices.player_wins]) / parseFloat(colsB[csvIndices.total_games]) * 100;
            const drawsA = parseFloat(colsA[csvIndices.player_draws_percent]);
            const drawsB = parseFloat(colsB[csvIndices.player_draws_percent]);
            const mistakesA = parseFloat(colsA[csvIndices.mistakes_per_1000moves]);
            const mistakesB = parseFloat(colsB[csvIndices.mistakes_per_1000moves]);
            return (winsB - winsA) || (drawsB - drawsA) || (mistakesA - mistakesB);
        }
    }
};

function showPane(screen) {
    const scrollPos = window.scrollY;
    currentScreen = screen;

    // Update UI based on screen
    switch(screen) {
        case Screen.LEADERBOARD_NEW:
            document.getElementById('leaderboard').style.display = 'block';
            document.getElementById('how-it-works').style.display = 'none';
            document.getElementById('considerations').style.display = 'none';
            document.querySelector('.dropbtn').textContent = 'Leaderboard ▼';
            buildTableGeneric(tableConfigs[Screen.LEADERBOARD_NEW]);
            break;

        case Screen.LEADERBOARD_OLD:
            document.getElementById('leaderboard').style.display = 'block';
            document.getElementById('how-it-works').style.display = 'none';
            document.getElementById('considerations').style.display = 'none';
            document.querySelector('.dropbtn').textContent = 'Leaderboard (O) ▼';
            buildTableGeneric(tableConfigs[Screen.LEADERBOARD_OLD]);
            break;

        case Screen.HOW_IT_WORKS:
            document.getElementById('leaderboard').style.display = 'none';
            document.getElementById('how-it-works').style.display = 'block';
            document.getElementById('considerations').style.display = 'none';
            break;

        case Screen.NOTES:
            document.getElementById('leaderboard').style.display = 'none';
            document.getElementById('how-it-works').style.display = 'none';
            document.getElementById('considerations').style.display = 'block';
            break;
    }

    // Update button states
    document.querySelectorAll('.button-container button, .dropbtn').forEach(button => {
        button.classList.remove('selected');
    });

    if (screen === Screen.LEADERBOARD_NEW || screen === Screen.LEADERBOARD_OLD) {
        document.querySelector('.dropbtn').classList.add('selected');
    } else if (screen === Screen.HOW_IT_WORKS) {
        document.querySelector('button[onclick="showPane(Screen.HOW_IT_WORKS)"]').classList.add('selected');
    } else if (screen === Screen.NOTES) {
        document.querySelector('button[onclick="showPane(Screen.NOTES)"]').classList.add('selected');
    }

    // Close dropdown
    document.querySelector('.dropdown-content').classList.remove('show');

    // Restore scroll position
    window.scrollTo(0, scrollPos);

    // Analytics
    gtag('event', 'page_view', {
        'page_title': document.title + ' - ' + screen,
        'page_path': '/' + screen
    });
}

function sortTable(columnIndex) {
    const table = document.querySelector('#leaderboard tbody');
    const rows = Array.from(table.rows);
    const isNumericColumn = columnIndex !== 0; // Assuming first column is not numeric

    // Determine the current sort order for the column
    const sortOrderObj = sortOrderState[currentScreen];
    const currentOrder = sortOrderObj[columnIndex] || 'asc';
    const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    sortOrderObj[columnIndex] = newOrder;

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
    const indicator = sortOrderObj[columnIndex] === 'asc' ? '▲' : '▼';
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

function showPlayerDetailsPopup(row, columns) {
    const popup = document.getElementById('popup');
    const totalGames = columns[csvIndices.total_games];

    const wins = columns[csvIndices.player_wins];
    const losses = columns[csvIndices.opponent_wins];
    const draws = columns[csvIndices.draws];

    const moeWins = columns[csvIndices.moe_black_llm_win_rate];
    const moeLosses = columns[csvIndices.moe_black_llm_loss_rate];
    const moeDraws = columns[csvIndices.moe_draw_rate];
    
    const averageMoves = columns[csvIndices.average_moves];
    const materialDiff = columns[csvIndices.material_diff_player_llm_minus_opponent];
    const mistakesPer1000Moves = columns[csvIndices.mistakes_per_1000moves];
    const completionTokensBlackPerMove = columns[csvIndices.completion_tokens_black_per_move];

    const moeAverageMoves = columns[csvIndices.moe_average_moves];
    const moeMaterialDiff = columns[csvIndices.moe_material_diff_llm_minus_rand];
    const moeMistakesPer1000Moves = columns[csvIndices.moe_mistakes_per_1000moves];
    const moeCompletionTokensBlackPerMove = columns[csvIndices.moe_completion_tokens_black_per_move];

    document.getElementById('total-games').textContent = `Games: ${parseInt(totalGames)}`;
    document.getElementById('wins').textContent = 
    `Wins: ${parseInt(wins)} (`+
    `${((parseInt(wins) / parseInt(totalGames))).toFixed(3)} ± ${parseFloat(moeWins).toFixed(3)})`;
    document.getElementById('losses').textContent = 
        `Losses: ${parseInt(losses)} (` +
        `${((parseInt(losses) / parseInt(totalGames))).toFixed(2)} ± ${parseFloat(moeLosses).toFixed(3)})`;
    const winsMinusLosses = ((parseInt(wins) - parseInt(losses)) / parseInt(totalGames)).toFixed(3);
    document.getElementById('wins_minus_losses').innerHTML = `&nbsp;&nbsp;&nbsp;Wins - Losses: ${winsMinusLosses}`;
    document.getElementById('draws').textContent = 
        `Draws: ${parseInt(draws)} (` +
        `${((parseInt(draws) / parseInt(totalGames))).toFixed(3)} ± ${parseFloat(moeDraws).toFixed(3)})`;
    document.getElementById('average-moves').textContent = `Average Moves: ${parseFloat(averageMoves).toFixed(2)} ± ${parseFloat(moeAverageMoves).toFixed(2)}`;
    document.getElementById('material-diff').textContent = `Material Diff: ${parseFloat(materialDiff).toFixed(2)} ± ${parseFloat(moeMaterialDiff).toFixed(2)}`;
    document.getElementById('mistakes-per-1000moves').textContent = `Mistakes/1k_Moves: ${parseFloat(mistakesPer1000Moves).toFixed(2)} ± ${parseFloat(moeMistakesPer1000Moves).toFixed(2)}`;
    document.getElementById('completion-tokens-black-per-move').textContent = `Compl.Toks/Move: ${parseFloat(completionTokensBlackPerMove).toFixed(2)} ± ${parseFloat(moeCompletionTokensBlackPerMove).toFixed(2)}`;

    const rect = row.getBoundingClientRect();
    if (window.innerWidth < 1350) {
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

function toggleDropdown() {
    document.querySelector('.dropdown-content').classList.toggle('show');
}

// Close the dropdown if clicked outside
window.onclick = function(event) {
    if (!event.target.matches('.dropbtn')) {
        var dropdowns = document.getElementsByClassName('dropdown-content');
        for (var i = 0; i < dropdowns.length; i++) {
            var openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
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
function buildTableGeneric(config) {
    const lines = data.trim().split('\n').filter(line => line.trim() !== '');
    const rawRows = lines.slice(1).map(row => row.split(','));

    // Clear table body
    const tbody = document.querySelector('#leaderboard tbody');
    tbody.innerHTML = '';

    // Separate bottom rows (e.g. Stockfish, random, etc.)
    const bottomRows = [];
    const normalRows = rawRows.filter(cols => {
        const playerName = cols[csvIndices.player];
        if (Object.values(SPECIAL_ROWS).includes(playerName)) {
            bottomRows.push(cols);
            return false;
        }
        return true;
    });

    // Sort main rows using config's defaultSortCompare
    normalRows.sort(config.defaultSortCompare);

    // Reassemble
    const allRows = [...normalRows, ...bottomRows];

    // Build rows
    allRows.forEach((cols, i) => {
        const tr = document.createElement('tr');
        config.columns.forEach((col, colIndex) => {
            // If it’s a rank column and row is in bottomRows, show blank
            const isBottomRow = bottomRows.includes(cols);
            const cellValue = (col.isRankColumn && isBottomRow)
                ? ''
                : col.getValue(cols, i);
            const td = document.createElement('td');
            td.textContent = cellValue;
            tr.appendChild(td);
        });
        // Add hover and click
        tr.addEventListener('mouseenter', () => showPlayerDetailsPopup(tr, cols));
        tr.addEventListener('mouseleave', hidePopup);
        tr.addEventListener('click', () => showPlayerDetailsPopup(tr, cols));

        tbody.appendChild(tr);
    });

    // Update table headers
    const theadCells = document.querySelectorAll('#leaderboard thead th');
    config.columns.forEach((col, i) => {
        theadCells[i].textContent = col.title;
        theadCells[i].setAttribute('title', col.tooltip || col.title);
    });
    theadCells.forEach((headerCell, idx) => {
        headerCell.addEventListener('click', () => sortTable(idx));
    });
}
