const Screen = {
    LEADERBOARD_NEW: 'leaderboard_new',
    LEADERBOARD_OLD: 'leaderboard_old',
    HOW_IT_WORKS: 'how_it_works',
    NOTES: 'notes'
};

let currentScreen = Screen.LEADERBOARD_NEW;

// data const is defined in data.js and imported in index.html, saving on tokens with AI codder

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

let currentSortOrder = {};

const SPECIAL_ROWS = {
    STOCKFISH: "Stockfish chess engine (as Black)",
    RANDOM_WHITE: "Random Player (as White)",
    RANDOM_BLACK: "Random Player (as Black)"
};

document.addEventListener('DOMContentLoaded', () => {
    buildTable();
    fetchAndAnimateBoard();
    
    // Select Leaderboard by default
    showPane(Screen.LEADERBOARD_NEW);
    
    // Initialize markdown rendering
    MinimalMD.render('considerations');
});



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
            buildTable();
            break;

        case Screen.LEADERBOARD_OLD:
            document.getElementById('leaderboard').style.display = 'block';
            document.getElementById('how-it-works').style.display = 'none';
            document.getElementById('considerations').style.display = 'none';
            document.querySelector('.dropbtn').textContent = 'Leaderboard (O) ▼';
            buildTable();
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

function buildTable() {
    const lines = data.trim().split('\n').filter(line => line.trim() !== '');
    const rows = lines.slice(1).map(row => row.split(','));

    // Clear the table body first
    const tbody = document.querySelector('#leaderboard tbody');
    tbody.innerHTML = ''; // Clear existing rows

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

    // Sort the remaining rows based on difficulty mode
    otherRows.sort((a, b) => {
        // Always use the new mode calculation
        const winsA = (parseInt(a[csvIndices.player_wins]) - parseInt(a[csvIndices.opponent_wins])) / parseInt(a[csvIndices.total_games]) * 100;
        const winsB = (parseInt(b[csvIndices.player_wins]) - parseInt(b[csvIndices.opponent_wins])) / parseInt(b[csvIndices.total_games]) * 100;

        const drawsA = parseFloat(a[csvIndices.player_draws_percent]);
        const drawsB = parseFloat(b[csvIndices.player_draws_percent]);
        const mistakesA = parseFloat(a[csvIndices.mistakes_per_1000moves]);
        const mistakesB = parseFloat(b[csvIndices.mistakes_per_1000moves]);

        // Hierarchical sorting: Wins DESC, Draws DESC, Mistakes ASC
        return winsB - winsA || drawsB - drawsA || mistakesA - mistakesB;
    });
    [...otherRows, ...bottomRows].forEach((columns, index) => {
        const isBottomRow = bottomRows.includes(columns); // Check if the row is a bottom row
        const player = columns[csvIndices.player];
        const player_wins_percent = parseFloat(columns[csvIndices.player_wins_percent]);
        const player_draws_percent = parseFloat(columns[csvIndices.player_draws_percent]);
        const wrong_actions_per_1000moves = parseFloat(columns[csvIndices.wrong_actions_per_1000moves]);
        const wrong_moves_per_1000moves = parseFloat(columns[csvIndices.wrong_moves_per_1000moves]);
        const mistakes = parseFloat(columns[csvIndices.mistakes_per_1000moves]);
        const tokens = parseFloat(columns[csvIndices.completion_tokens_black_per_move]);

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${isBottomRow ? '' : index + 1}</td> <!-- Empty rank for bottom rows -->
            <td>${player}</td> <!-- Player first -->
            <td>${((parseInt(columns[csvIndices.player_wins]) - parseInt(columns[csvIndices.opponent_wins])) / parseInt(columns[csvIndices.total_games]) * 100).toFixed(2)}%</td>
            <td>${parseFloat(columns[csvIndices.average_moves]).toFixed(1)}</td>
            <td>${mistakes.toFixed(2)}</td>
            <td>${tokens.toFixed(2)}</td>
        `;
        tbody.appendChild(tr);

        // Add event listeners for hover and tap
        tr.addEventListener('mouseenter', () => showPopup(tr, columns));
        tr.addEventListener('mouseleave', hidePopup);
        tr.addEventListener('click', () => showPopup(tr, columns));
    });

    // Update column headers for the new format
    const winsHeader = document.querySelector('#leaderboard th:nth-child(3)');
    const drawsMovesHeader = document.querySelector('#leaderboard th:nth-child(4)');
    
    winsHeader.textContent = 'Wins-Losses';
    winsHeader.title = 'Difference between wins and losses as percentage of total games';
    drawsMovesHeader.textContent = 'Avg Moves';
    drawsMovesHeader.title = 'Average number of moves per game';

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
