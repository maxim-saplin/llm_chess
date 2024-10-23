```
Proxy (to Player_Black):

You are a professional chess player and you play as black. Now is your turn to make a move. Before making a move you can pick one of the following actions:
- 'get_current_board' to get the schema and current status of the board
- 'get_legal_moves' to get a UCI formatted list of available moves
- 'make_move <UCI formatted move>' when you are ready to complete your turn (e.g., 'make_move e2e4')

--------------------------------------------------------------------------------
Player_Black (to Proxy):

get_current_board

--------------------------------------------------------------------------------
Proxy (to Player_Black):

♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜
♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟
⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘
⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘
⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘ ⭘
⭘ ⭘ ♘ ⭘ ⭘ ⭘ ⭘ ⭘
♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙
♖ ⭘ ♗ ♕ ♔ ♗ ♘ ♖

--------------------------------------------------------------------------------
Player_Black (to Proxy):

It's your move. Would you like to see the available legal moves or make a move?

--------------------------------------------------------------------------------
Proxy (to Player_Black):

Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>

--------------------------------------------------------------------------------
Player_Black (to Proxy):

get_legal_moves

--------------------------------------------------------------------------------
Proxy (to Player_Black):

g8h6,g8f6,b8c6,b8a6,h7h6,g7g6,f7f6,e7e6,d7d6,c7c6,b7b6,a7a6,h7h5,g7g5,f7f5,e7e5,d7d5,c7c5,b7b5,a7a5

--------------------------------------------------------------------------------
Player_Black (to Proxy):

Black, it's your move. What move would you like to make?

--------------------------------------------------------------------------------
Proxy (to Player_Black):

Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>

--------------------------------------------------------------------------------
Player_Black (to Proxy):

My apologies for the confusion. Let me provide you with the available legal moves in UCI format.

Available legal moves: g8h6, g8f6, b8c6, b8a6, h7h6, g7g6, f7f6, e7e6, d7d6, c7c6, b7b6, a7a6, h7h5, g7g5, f7f5, e7e5, d7d5, c7c5, b7b5, a7a5

Please let me know your move in UCI format.

--------------------------------------------------------------------------------
Invalid action. Pick one, reply exactly with the name and space delimitted argument: get_current_board, get_legal_moves, make_move <UCI formatted move>
Proxy (to Player_Black):

Too many wrong actions
```