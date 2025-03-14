The recently added PGN feature changed the error prompt used by the proxy adding san() and lan() texts, which can be confusion and which is DIFFERENT from how all the rest models were prompted to course correct before, discarding logs as invalid:
```
--------------------------------------------------------------------------------
Proxy (to Player_Black):

Failed to make move: san() and lan() expect move to be legal or null, but got e7e5 in rnbqkbnr/pppp1ppp/8/2P1p3/8/8/PP1PPPPP/RNBQKBNR b KQkq - 0 2

--------------------------------------------------------------------------------
[_ag.oai.client: 03-13 23:23:10] {349} WARNING - Model google_gemma-3-27b-it@q4_k_m is not found. The cost will be 0. In your config_list, add field {"price" : [prompt_price_per_1k, completion_token_price_per_1k]} for customized pricing.
Player_Black (to Proxy):

You are right to point that out! My apologies. I made an error in the move format. It should be UCI format, not SAN or LAN. Let me try again with the correct format.

```tool_code
make_move e7e5
```
```