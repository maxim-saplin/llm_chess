const data = `
Player,total_games,player_wins,opponent_wins,draws,player_wins_percent,player_draws_percent,average_moves,moe_average_moves,total_moves,player_wrong_actions,player_wrong_moves,wrong_actions_per_1000moves,wrong_moves_per_1000moves,mistakes_per_1000moves,moe_mistakes_per_1000moves,player_avg_material,opponent_avg_material,material_diff_player_llm_minus_opponent,moe_material_diff_llm_minus_rand,completion_tokens_black_per_move,moe_completion_tokens_black_per_move,std_dev_black_llm_win_rate,moe_black_llm_win_rate,std_dev_draw_rate,moe_draw_rate,std_dev_black_llm_loss_rate,moe_black_llm_loss_rate
amazon.nova-lite-v1,42,0,42,0,0.0,0.0,4.619047619047619,0.7845472344885497,194,50,46,424.6031746031746,196.82539682539684,621.4285714285714,161.20153522640408,38.95238095238095,38.92857142857143,0.023809523809523808,0.15648233404192521,534.3814432989691,189.87818676853868,0.0,0.0,0.0,0.0,0.0,0.0
amazon.nova-pro-v1,33,0,33,0,0.0,0.0,11.757575757575758,2.8277690947564778,388,11,88,49.494949494949495,327.6307026307026,377.12565212565215,74.47062994874662,38.45454545454545,38.90909090909091,-0.45454545454545453,0.40090909090909094,177.19329896907217,18.063794332128413,0.0,0.0,0.0,0.0,0.0,0.0
claude-v3-7-sonnet,39,2,9,28,5.128205128205128,71.7948717948718,165.46153846153845,18.863370705290265,6453,0,12,0.0,8.954924557246763,8.954924557246763,9.736789116762221,13.794871794871796,10.076923076923077,3.717948717948718,2.0005121459218462,108.53835425383542,2.0375463636114186,0.035319858036984335,0.06922692175248929,0.07205737677223015,0.14123245847357108,0.0674660014851561,0.13223336291090593
claude-v3-5-sonnet-v1,60,4,8,48,6.666666666666667,80.0,183.38333333333333,10.151169172222898,11003,0,3,0.0,1.6666666666666667,1.6666666666666667,3.266666666666666,13.2,17.366666666666667,-4.166666666666667,3.0048638788338065,80.42406616377352,1.28149031781466,0.03220305943597653,0.063117996494514,0.05163977794943222,0.10121396478088715,0.043885372573625556,0.08601533024430609
claude-v3-5-sonnet-v2,60,2,5,53,3.3333333333333335,88.33333333333333,188.2,9.393916954679366,11292,0,8,0.0,2.9828722002635044,2.9828722002635044,4.561594266967543,10.816666666666666,13.833333333333334,-3.0166666666666666,2.559978723722791,90.8544987601842,1.142357874866914,0.023174059571793568,0.04542115676071539,0.04144384867012948,0.08122994339345378,0.03568120160740314,0.06993515515051014
claude-v3-haiku,40,0,40,0,0.0,0.0,33.35,7.952752988906678,1334,7,4,13.203463203463203,13.541666666666666,26.74512987012987,30.686878575611857,36.725,37.15,-0.425,1.0732781200960555,210.64017991004496,81.16412124116572,0.0,0.0,0.0,0.0,0.0,0.0
claude-v3-opus,30,0,5,25,0.0,83.33333333333334,165.6,23.78205127121432,4968,1,7,1.8518518518518516,7.457634521313766,9.309486373165617,12.310850869238884,15.633333333333333,21.633333333333333,-6.0,3.1590075554883033,72.8623188405797,4.832303432016992,0.0,0.0,0.06804138174397716,0.13336110821819522,0.06804138174397717,0.13336110821819525
chat-bison-32k@002,36,0,36,0,0.0,0.0,26.444444444444443,6.178575807768785,952,76,30,244.82651414285934,65.19321180951513,310.0197259523745,146.62042674350698,37.05555555555556,36.888888888888886,0.16666666666666666,1.5010426006242756,31.644957983193276,41.8119627763183,0.0,0.0,0.0,0.0,0.0,0.0
deephermes-3-llama-3-8b-preview@q8,42,0,42,0,0.0,0.0,3.2857142857142856,0.49666202867916864,138,118,7,1044.642857142857,65.47619047619048,1110.1190476190477,134.16666666666666,39.0,39.0,0.0,0.0,101.35507246376811,29.736101573105277,0.0,0.0,0.0,0.0,0.0,0.0
deepseek-chat-v3,70,0,68,2,0.0,2.857142857142857,57.75714285714286,11.860508178862721,4043,10,180,1.9779146503284433,96.34064766615487,98.31856231648331,20.819617008528166,32.17142857142857,30.52857142857143,1.6428571428571428,1.424718024479006,246.92604501607718,8.419067135512611,0.0,0.0,0.019912344355347705,0.0390281949364815,0.019912344355347705,0.0390281949364815
deepseek-r1-distill-qwen-14b@q8_0,30,0,30,0,0.0,0.0,2.6,0.3828824734899041,78,82,8,1175.0,116.66666666666667,1291.6666666666667,126.69910352977656,39.0,39.0,0.0,0.0,3073.0641025641025,294.8332117524135,0.0,0.0,0.0,0.0,0.0,0.0
deepseek-r1-distill-qwen-32b@q4_k_m,30,0,30,0,0.0,0.0,3.6666666666666665,0.8422855241630117,110,73,7,894.4444444444445,65.83333333333333,960.2777777777778,174.45852569031015,39.0,38.96666666666667,0.03333333333333333,0.06533333333333333,2173.827272727273,409.7170270212998,0.0,0.0,0.0,0.0,0.0,0.0
deepseek-reasoner-r1,31,7,18,6,22.58064516129032,19.35483870967742,91.7741935483871,22.88780015438446,2845,9,44,6.105746600504369,46.825282688770564,52.93102928927493,32.80503218251817,21.93548387096774,10.806451612903226,11.129032258064516,3.6034642290753296,4584.972583479789,190.77372058839293,0.07509518648353262,0.14718656550772394,0.07095828146194513,0.13907823166541247,0.08862686513992751,0.17370865567425792
gemini-1.5-flash-001,30,0,20,10,0.0,33.33333333333333,84.13333333333334,33.52922259395211,2524,18,36,114.57671957671957,229.15343915343914,343.73015873015873,121.09496577679688,29.266666666666666,35.666666666666664,-6.4,3.1275403136959086,19.914817749603802,4.41176537691356,0.0,0.0,0.08606629658238704,0.1686899413014786,0.08606629658238704,0.1686899413014786
gemini-1.5-pro-preview-0409,40,0,37,3,0.0,7.5,65.65,18.51170654145433,2626,14,71,4.7327303719316784,77.71717780731329,82.44990817924497,22.518459167327492,29.75,33.075,-3.325,2.355334975359948,13.383472962680884,0.3541643238497577,0.0,0.0,0.04164582812239421,0.08162582311989265,0.041645828122394195,0.08162582311989262
gemini-2.0-flash-001,67,3,41,23,4.477611940298507,34.32835820895522,158.80597014925374,10.89602696476666,10640,18,95,2.1359906619745535,11.927216140577817,14.063206802552372,4.203592989246968,14.671641791044776,16.65671641791045,-1.9850746268656716,2.288594271817639,93.77387218045112,3.0662608323004634,0.02526611161284531,0.049521578761176806,0.058006685713137024,0.11369310399774857,0.05953418302796191,0.11668699873480534
gemini-2.0-flash-exp,30,0,28,2,0.0,6.666666666666667,85.86666666666666,26.34577194255355,2576,0,81,0.0,117.39474439973138,117.39474439973138,46.898865011506324,26.933333333333334,27.166666666666668,-0.23333333333333334,1.8811008597213612,168.15023291925465,16.07928337131627,0.0,0.0,0.04554200340426488,0.08926232667235917,0.045542003404264876,0.08926232667235916
gemini-2.0-flash-lite-001,66,1,65,0,1.5151515151515151,0.0,84.21212121212122,14.68032684172875,5558,17,172,9.713026443697206,123.68393202231611,133.39695846601333,53.91282898628674,26.40909090909091,30.12121212121212,-3.712121212121212,1.8624340549093443,150.15005397625046,6.975579812642362,0.015036292831784037,0.029471133950296713,0.0,0.0,0.015036292831784029,0.029471133950296696
gemini-2.0-flash-lite-preview-02-05,39,0,39,0,0.0,0.0,51.256410256410255,14.883736764331012,1999,21,93,17.163418704749315,140.3819035902136,157.54532229496292,66.66861818129593,32.794871794871796,34.23076923076923,-1.435897435897436,1.638422260188671,144.00350175087544,8.349602593950689,0.0,0.0,0.0,0.0,0.0,0.0
gemini-2.0-flash-thinking-exp-01-21,33,0,33,0,0.0,0.0,40.63636363636363,8.571846527590305,1341,7,1,49.62982093663912,0.6184291898577613,50.24825012649688,89.00386667429298,33.21212121212121,33.72727272727273,-0.5151515151515151,1.8415713237103288,17.76957494407159,8.802824391986771,0.0,0.0,0.0,0.0,0.0,0.0
gemini-2.0-flash-thinking-exp-1219,30,0,30,0,0.0,0.0,2.3333333333333335,0.3300286763344439,70,89,1,1386.111111111111,5.555555555555555,1391.6666666666667,101.54969717418454,39.0,39.0,0.0,0.0,724.5428571428571,78.2856170519377,0.0,0.0,0.0,0.0,0.0,0.0
gemma-2-27b-it@q6_k_l,30,0,22,8,0.0,26.666666666666668,108.93333333333334,25.251073216902363,3268,8,52,3.831407649251797,48.07826143763394,51.90966908688574,24.91880310611584,25.466666666666665,26.333333333333332,-0.8666666666666667,2.669171283562778,55.04436964504284,2.7293574175775106,0.0,0.0,0.08073734277593311,0.15824519184082889,0.08073734277593311,0.15824519184082889
gemma-2-9b-it-8bit,30,0,26,4,0.0,13.333333333333334,69.16666666666667,26.06307596164304,2075,45,31,163.66922692296475,71.24054344481173,234.90977036777647,135.3576928738708,32.0,34.13333333333333,-2.1333333333333333,1.8045446926836475,58.12433734939759,4.686687185745504,0.0,0.0,0.06206328908341752,0.12164404660349833,0.06206328908341751,0.12164404660349831
gemma2-9b-it-groq,35,0,35,0,0.0,0.0,14.742857142857142,5.266802758231758,516,83,22,414.8091421576605,61.745489264286256,476.55463142194674,153.40236127109787,38.714285714285715,38.31428571428572,0.4,0.5636118814762305,20.217054263565892,1.5078879385119421,0.0,0.0,0.0,0.0,0.0,0.0
gpt-35-turbo-0125,30,0,30,0,0.0,0.0,2.8666666666666667,0.6693575120421097,86,90,0,1285.0,0.0,1285.0,144.68382174888134,39.0,39.0,0.0,0.0,82.02325581395348,16.04020377336009,0.0,0.0,0.0,0.0,0.0,0.0
gpt-35-turbo-0301,30,0,30,0,0.0,0.0,2.2666666666666666,0.24744716530374364,68,90,0,1400.0,0.0,1400.0,92.79268698890385,39.0,39.0,0.0,0.0,67.05882352941177,14.051924570603521,0.0,0.0,0.0,0.0,0.0,0.0
gpt-35-turbo-0613,30,0,30,0,0.0,0.0,4.133333333333334,1.0109755995251561,124,90,0,1051.6666666666667,0.0,1051.6666666666667,188.72526363499827,39.0,38.96666666666667,0.03333333333333333,0.06533333333333333,93.62903225806451,19.57608849106176,0.0,0.0,0.0,0.0,0.0,0.0
gpt-35-turbo-1106,30,0,30,0,0.0,0.0,3.6,0.8694574341996607,108,88,2,1130.2777777777778,8.88888888888889,1139.1666666666667,176.0411046784201,39.0,39.0,0.0,0.0,48.324074074074076,8.190238149115658,0.0,0.0,0.0,0.0,0.0,0.0
gpt-4-0613,33,0,3,30,0.0,90.9090909090909,192.87878787878788,10.45545282404063,6365,0,0,0.0,0.0,0.0,0.0,15.151515151515152,18.78787878787879,-3.6363636363636362,3.0082751801038166,6.56967792615868,0.050440077282743946,0.0,0.0,0.05004380750574367,0.09808586271125759,0.050043807505743665,0.09808586271125758
gpt-4-32k-0613,33,0,1,32,0.0,96.96969696969697,198.6969696969697,2.553939393939394,6557,0,0,0.0,0.0,0.0,0.0,13.787878787878787,17.727272727272727,-3.9393939393939394,3.8704449219024233,6.6565502516394695,0.13102619518240477,0.0,0.0,0.029840361449535197,0.05848710844108898,0.02984036144953521,0.05848710844108901
gpt-4-turbo-2024-04-09,30,0,2,28,0.0,93.33333333333333,192.86666666666667,10.710544763647627,5786,0,0,0.0,0.0,0.0,0.0,15.433333333333334,20.8,-5.366666666666666,3.719412378917461,6.032837884548911,0.03095803458091743,0.0,0.0,0.045542003404264876,0.08926232667235916,0.04554200340426488,0.08926232667235917
gpt-4o-2024-05-13,60,0,12,48,0.0,80.0,184.28333333333333,9.43337606785952,11057,1,16,0.08333333333333333,3.461510791480984,3.5448441248143174,3.4918821253204784,13.633333333333333,17.35,-3.716666666666667,1.9141124636605054,31.334720086822827,0.8692038868007278,0.0,0.0,0.05163977794943222,0.10121396478088715,0.051639777949432225,0.10121396478088716
gpt-4o-2024-08-06,60,1,9,50,1.6666666666666667,83.33333333333334,186.9,8.050166925314263,11214,0,1,0.0,0.15723270440251572,0.15723270440251572,0.3081761006289308,14.483333333333333,19.333333333333332,-4.85,2.5698508958923365,7.70322810772249,0.3882429219180587,0.01652719420071502,0.032393300633401435,0.04811252243246881,0.09430054396763886,0.046097722286464436,0.0903515356814703
gpt-4o-2024-11-20,71,3,6,62,4.225352112676056,87.32394366197182,189.71830985915494,7.5917787417310905,13470,1,1,0.07042253521126761,0.07042253521126761,0.14084507042253522,0.19380199803298997,11.901408450704226,19.901408450704224,-8.0,2.499408831512414,50.575278396436524,0.2531172633271257,0.023874130344503686,0.046793295475227224,0.039484766709934636,0.07739014275147188,0.03300994345777757,0.06469948917724404
gpt-4o-mini-2024-07-18,30,0,12,18,0.0,60.0,149.36666666666667,25.1361939516602,4481,13,24,4.701451970801815,31.083346306256523,35.784798277058336,27.63415379469353,20.433333333333334,24.866666666666667,-4.433333333333334,3.093589178876671,108.21624637357732,8.09483715881323,0.0,0.0,0.08944271909999159,0.17530772943598352,0.08944271909999159,0.17530772943598352
granite-3.1-8b-instruct,30,0,30,0,0.0,0.0,4.2,0.8885465854319393,126,47,12,447.5,91.66666666666667,539.1666666666666,175.53872863001527,38.96666666666667,39.0,-0.03333333333333333,0.06533333333333333,469.12698412698415,204.83928800495804,0.0,0.0,0.0,0.0,0.0,0.0
grok-2-1212,49,2,32,15,4.081632653061225,30.612244897959183,114.14285714285714,19.00840515842049,5593,1,93,0.5102040816326531,32.28054641491559,32.79075049654825,9.452880848247577,25.3265306122449,22.387755102040817,2.938775510204082,2.5202645363797296,66.22867870552476,1.0367678864743854,0.028266354853739527,0.055402055513329475,0.06584017370633362,0.1290467404644139,0.06799943900694229,0.13327890045360688
internlm3-8b-instruct,30,0,30,0,0.0,0.0,3.6,0.6880085538094294,108,15,39,166.66666666666666,412.5,579.1666666666666,212.25208436669746,39.0,39.0,0.0,0.0,1543.898148148148,429.66933049762696,0.0,0.0,0.0,0.0,0.0,0.0
llama-2-7b-chat,30,0,30,0,0.0,0.0,2.1333333333333333,0.1815765778944155,64,88,2,1425.0,25.0,1450.0,68.0912167104058,39.0,39.0,0.0,0.0,116.3125,68.49300805930116,0.0,0.0,0.0,0.0,0.0,0.0
llama-3-70b-instruct-awq,30,0,15,15,0.0,50.0,148.3,22.339760638362048,4449,2,41,0.606060606060606,22.27814337138526,22.884203977445868,14.73482801691518,21.566666666666666,26.966666666666665,-5.4,3.0863249581219465,41.60890087660148,2.695118045011193,0.0,0.0,0.09128709291752768,0.17892270211835426,0.09128709291752768,0.17892270211835426
llama-3.1-tulu-3-8b@q8_0,42,0,42,0,0.0,0.0,3.5,0.6450285176780063,147,7,26,54.56349206349206,184.52380952380952,239.0873015873016,133.73984580714574,39.0,39.0,0.0,0.0,1996.3333333333333,593.7799618567382,0.0,0.0,0.0,0.0,0.0,0.0
llama-3.3-70b,42,0,38,4,0.0,9.523809523809524,68.71428571428571,20.992987447031435,2886,2,100,3.3068783068783065,107.34967736957964,110.65655567645794,39.03949591031765,30.904761904761905,33.45238095238095,-2.5476190476190474,1.745939462594872,102.98163548163548,5.654537714170008,0.0,0.0,0.04529474910530199,0.0887777082463919,0.04529474910530199,0.0887777082463919
llama3-8b-8192,60,0,60,0,0.0,0.0,15.033333333333333,2.6672990154208023,902,104,66,206.94153142179456,89.71030395043553,296.6518353722301,52.862007385599405,38.2,38.68333333333333,-0.48333333333333334,0.5521978615883527,57.019955654102,7.383641610185949,0.0,0.0,0.0,0.0,0.0,0.0
llama3.1-8b,90,0,87,3,0.0,3.3333333333333335,27.066666666666666,4.595073421102033,2436,44,188,35.03988017468409,126.64663826670215,161.68651844138626,26.330820997178886,37.2,37.833333333333336,-0.6333333333333333,0.8031280792068516,162.1013957307061,85.99671862172504,0.0,0.0,0.01892154040658489,0.037086219196906384,0.018921540406584888,0.03708621919690638
ministral-8b-instruct-2410,30,0,30,0,0.0,0.0,9.4,2.4731626920098533,282,56,34,453.517871017871,152.81204906204906,606.32992007992,187.55272893638383,38.766666666666666,38.6,0.16666666666666666,0.5645010681466399,72.11347517730496,12.893671903384732,0.0,0.0,0.0,0.0,0.0,0.0
mistral-nemo-12b-instruct-2407,30,0,30,0,0.0,0.0,6.733333333333333,1.83656043667174,202,79,11,733.9484126984127,42.5,776.4484126984127,194.25541975034824,38.766666666666666,38.666666666666664,0.1,0.5091145344570338,47.698019801980195,18.785382381523522,0.0,0.0,0.0,0.0,0.0,0.0
mistral-small-24b-instruct-2501@q4_k_m,42,0,42,0,0.0,0.0,20.333333333333332,5.060551294453405,854,3,123,4.8840048840048835,221.71666727807045,226.60067216207534,39.781794364091574,37.404761904761905,37.73809523809524,-0.3333333333333333,0.9199198739704155,110.94847775175644,4.957864158549713,0.0,0.0,0.0,0.0,0.0,0.0
mistral-small-instruct-2409,30,0,30,0,0.0,0.0,9.066666666666666,1.9050094236550537,272,58,32,365.49603174603175,127.91847041847042,493.41450216450215,136.37444332800882,38.86666666666667,38.833333333333336,0.03333333333333333,0.17539166898086328,88.24264705882354,21.22893063108001,0.0,0.0,0.0,0.0,0.0,0.0
o1-2024-12-17-low,48,27,0,21,56.25,43.75,127.70833333333333,15.616335644061655,6130,0,0,0.0,0.0,0.0,0.0,19.270833333333332,3.9583333333333335,15.3125,3.429829339726015,1641.2393148450244,32.826117011842776,0.071602745233685,0.1403413806580226,0.071602745233685,0.1403413806580226,0.0,0.0
o1-mini-2024-09-12,30,9,6,15,30.0,50.0,142.73333333333332,21.989890670688023,4282,2,8,0.9450830140485312,3.3492881937409673,4.294371207789498,4.291104179211649,17.666666666666668,7.033333333333333,10.633333333333333,3.1596830822214796,1221.1361513311538,79.49027019438729,0.08366600265340755,0.1639853652006788,0.09128709291752768,0.17892270211835426,0.07302967433402216,0.14313816169468344
o1-preview-2024-09-12,30,14,3,13,46.666666666666664,43.333333333333336,124.8,22.015672027094645,3744,4,10,2.9231524976205825,6.364050790877427,9.28720328849801,10.209580823090507,17.8,4.033333333333333,13.766666666666667,4.33577735498845,2660.071848290598,95.70634026690988,0.09108400680852977,0.17852465334471834,0.09047201327032126,0.17732514600982965,0.05477225575051661,0.10735362127101256
o3-mini-2025-01-31-low,65,3,25,37,4.615384615384616,56.92307692307692,152.8923076923077,14.90122660174948,9938,4,33,0.5806836841319599,8.633730933955821,9.214414618087782,5.91941342232706,17.107692307692307,10.6,6.507692307692308,2.177871845437176,678.9544173878044,15.421011914946893,0.026024742262539098,0.05100849483457663,0.06142000433230403,0.1203832084913159,0.06034342619636432,0.11827311534487406
o3-mini-2025-01-31-medium,44,16,1,27,36.36363636363637,61.36363636363637,135.77272727272728,17.999363511927818,5974,3,4,1.5910729501212557,2.8297682709447414,4.420841221065998,6.70969503922503,18.5,1.4545454545454546,17.045454545454547,3.504274614345527,2514.2470706394374,78.94218325908832,0.07252036683795142,0.1421399190023848,0.07340528480781205,0.14387435822331163,0.022467523936912755,0.044036346916349
phi-4,30,0,30,0,0.0,0.0,7.733333333333333,1.6570861376020711,232,44,46,264.8484848484849,232.67316017316017,497.52164502164504,77.50941569812285,39.0,39.0,0.0,0.0,333.5431034482759,40.98349110044259,0.0,0.0,0.0,0.0,0.0,0.0
qwen-max-2025-01-25,60,0,2,58,0.0,96.66666666666667,196.5,4.9832298649576305,11790,0,0,0.0,0.0,0.0,0.0,18.533333333333335,21.383333333333333,-2.85,2.312460733519122,6.06234096692112,0.03740259781050197,0.0,0.0,0.023174059571793564,0.045421156760715384,0.023174059571793568,0.04542115676071539
qwen-plus-2025-01-25,33,0,30,3,0.0,9.090909090909092,87.57575757575758,21.2601060288111,2890,2,89,1.1784511784511784,64.85346359080525,66.03191476925642,23.301275292440128,28.515151515151516,25.90909090909091,2.606060606060606,2.7678388270035046,440.41384083044983,7.514843740905844,0.0,0.0,0.050043807505743665,0.09808586271125758,0.05004380750574367,0.09808586271125759
qwen-turbo-2024-11-01,33,0,33,0,0.0,0.0,20.424242424242426,4.76985475846972,674,4,95,10.267145135566189,220.3954220340021,230.6625671695683,60.2042865302614,38.0,38.333333333333336,-0.3333333333333333,1.0470024553047341,192.3679525222552,26.099217852600777,0.0,0.0,0.0,0.0,0.0,0.0
qwen2.5-14b-instruct-1m,42,0,42,0,0.0,0.0,7.428571428571429,1.6807586362996725,312,48,49,241.01473922902494,174.8015873015873,415.81632653061223,101.60180969161259,38.857142857142854,38.95238095238095,-0.09523809523809523,0.1743062128168651,235.26602564102564,84.93704953378911,0.0,0.0,0.0,0.0,0.0,0.0
qwen2.5-14b-instruct@q8_0,30,0,30,0,0.0,0.0,13.266666666666667,3.58823002291074,398,29,59,156.93121693121694,212.67376142376142,369.60497835497836,109.70238708464787,38.56666666666667,38.4,0.16666666666666666,0.6379452167834305,150.63065326633165,18.310920002059007,0.0,0.0,0.0,0.0,0.0,0.0
qwen2.5-72b-instruct,30,0,28,2,0.0,6.666666666666667,64.1,18.287301879254592,1923,10,71,8.232851372597288,81.14434750949682,89.37719888209412,34.98270454165298,30.666666666666668,32.733333333333334,-2.066666666666667,2.1095896497711246,219.46541861674467,10.325241284331659,0.0,0.0,0.04554200340426488,0.08926232667235917,0.045542003404264876,0.08926232667235916
qwen2.5-7b-instruct-1m,42,0,42,0,0.0,0.0,9.666666666666666,2.1119425548564403,406,33,93,180.37732769875626,403.05560841275127,583.4329361115075,147.80333527597642,38.73809523809524,38.714285714285715,0.023809523809523808,0.1946075196925011,140.79064039408868,16.12567238726695,0.0,0.0,0.0,0.0,0.0,0.0
qwq-32b-preview@q4_k_m,30,0,30,0,0.0,0.0,7.966666666666667,1.734041040316496,239,44,17,308.6381673881674,97.35569985569985,405.9938672438672,157.30378191102815,38.86666666666667,38.96666666666667,-0.1,0.21736435854991518,2908.0,407.07021980501514,0.0,0.0,0.0,0.0,0.0,0.0
sky-t1-32b-preview,30,0,30,0,0.0,0.0,13.833333333333334,3.3279335113458464,415,9,59,24.57070707070707,185.1043159738812,209.67502304458827,60.69321478449664,38.766666666666666,38.8,-0.03333333333333333,0.34507228405951934,1216.1590361445783,483.6306332021484,0.0,0.0,0.0,0.0,0.0,0.0
`
+
`
Stockfish chess engine (as Black),1000,1000,0,0,100.000,0.000,57.922,30.961727092404658,-,0,0,-,-,-,-,35.113,19.125,15.988,5.572188105249165,-,-,-,-,-
Random Player (as White),1000,105,0,895,10.500,89.500,190.073,32.05006829755403,-,0,0,-,-,-,-,10.555,11.076,-0.521,7.228224001940049,-,-,-,-,-
Random Player (as Black),1000,0,105,895,0.000,89.500,190.073,32.05006829755403,-,0,0,-,-,-,-,11.076,10.555,0.521,7.491217680880882,-,-,-,-,-
`
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
});

let lbVersion = 'new'; // Default view


function showPane(paneId, view, event) {
    if (event) {
        event.preventDefault();
    }
    
    const scrollPos = window.scrollY;

    if (view) {
        lbVersion = view;
        // Update dropdown items
        document.querySelectorAll('.dropdown-content a').forEach(item => {
            item.classList.remove('active'); // First remove active from all items
            if (item.textContent.toLowerCase().includes(view.toLowerCase())) {
                item.classList.add('active');
                // Remove any existing dots and add a new one
                item.textContent = item.textContent.replace(/^[•\s]*/, ''); // Remove existing dots and spaces
                item.textContent = '• ' + item.textContent;
            } else {
                // Remove any dots from non-active items
                item.textContent = item.textContent.replace(/^[•\s]*/, '');
            }
        });

        // Update the column headers based on view
        const winsHeader = document.querySelector('#leaderboard th:nth-child(3)');
        winsHeader.textContent = lbVersion === 'old' ? 'Wins' : 'Wins-Losses';
        winsHeader.innerHTML += '&nbsp;&nbsp;';
        
        const drawsMovesHeader = document.querySelector('#draws-moves-header');
        drawsMovesHeader.textContent = lbVersion === 'old' ? 'Draws' : 'Avg Moves';
        drawsMovesHeader.innerHTML += '&nbsp;&nbsp;';
        drawsMovesHeader.title = lbVersion === 'old' ? 
            'Percentage of games without a winner' : 
            'Average number of moves per game';
        
        // Update dropdown button text
        const dropBtn = document.querySelector('.dropbtn');
        dropBtn.textContent = lbVersion === 'old' ? 'Leaderboard (O) ▼' : 'Leaderboard ▼';
        
        buildTable();
    }
    
    document.getElementById('leaderboard').style.display = paneId === 'leaderboard' ? 'block' : 'none';
    document.getElementById('how-it-works').style.display = paneId === 'how-it-works' ? 'block' : 'none';
    document.getElementById('considerations').style.display = paneId === 'considerations' ? 'block' : 'none';
    
    document.querySelectorAll('.button-container button').forEach(button => {
        button.classList.remove('selected');
    });
    if (paneId === 'leaderboard') {
        document.querySelector('.dropbtn').classList.add('selected');
    }

    // Update dropdown button text
    if (difficulty) {
        document.querySelector('.dropbtn').textContent = `Leaderboard (${difficulty}) ▼`;
    }

    // Close dropdown
    document.getElementById('leaderboardDropdown').classList.remove('show');

    // Restore scroll position
    window.scrollTo(0, scrollPos);

    gtag('event', 'page_view', {
        'page_title': document.title + ' - ' + paneId + (difficulty ? ' - ' + difficulty : ''),
        'page_path': '/' + paneId + (difficulty ? '/' + difficulty : '')
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
        let winsA, winsB;
        
        if (lbVersion === 'old') {
            winsA = parseFloat(a[csvIndices.player_wins_percent]);
            winsB = parseFloat(b[csvIndices.player_wins_percent]);
        } else { // 'new' mode
            winsA = (parseInt(a[csvIndices.player_wins]) - parseInt(a[csvIndices.opponent_wins])) / parseInt(a[csvIndices.total_games]) * 100;
            winsB = (parseInt(b[csvIndices.player_wins]) - parseInt(b[csvIndices.opponent_wins])) / parseInt(b[csvIndices.total_games]) * 100;
        }

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
            <td>${lbVersion === 'old' ? 
                player_wins_percent.toFixed(2) : 
                ((parseInt(columns[csvIndices.player_wins]) - parseInt(columns[csvIndices.opponent_wins])) / parseInt(columns[csvIndices.total_games]) * 100).toFixed(2)}%</td>
            <td>${lbVersion === 'old' ? 
                player_draws_percent.toFixed(2) + '%' : 
                parseFloat(columns[csvIndices.average_moves]).toFixed(1)}</td>
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
