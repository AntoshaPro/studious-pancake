# find_best_chain_smart.py


def find_best_chain_smart(
    board,
    board_hash,
    is_move_blacklisted,
    evaluate_chain_smart,
    find_all_chains,
    optimal_lengths,
):
    """
    board                - текущая доска (матрица чисел)
    board_hash           - Zobrist-хэш доски
    is_move_blacklisted  - функция проверки блэклиста
    evaluate_chain_smart - функция оценки цепочки
    find_all_chains      - функция поиска всех цепочек
    optimal_lengths      - ПОРЯДОК длин цепочек, приходит снаружи (из JSON)
    """
    # 1) ищем все цепочки
    chains = find_all_chains()
    if not chains:
        return None

    # 2) группируем по длине
    chains_by_length: dict[int, list[list[tuple[int, int]]]] = {}
    for chain in chains:
        length = len(chain)
        if length not in chains_by_length:
            chains_by_length[length] = []
        chains_by_length[length].append(chain)

    # 3) перебор длин в порядке optimal_lengths
    for length in optimal_lengths:
        if length not in chains_by_length:
            continue

        valid_chains: list[list[tuple[int, int]]] = []

        for chain in chains_by_length[length]:
            move_key = (
                f"chain_{len(chain)}_{chain[0][0]}_{chain[0][1]}_"
                f"{chain[-1][0]}_{chain[-1][1]}"
            )
            if is_move_blacklisted(board_hash, move_key):
                continue

            score = evaluate_chain_smart(chain)
            print(
                f"[FBC] len={len(chain)} score={score:.1f} "
                f"[FBC] from {chain[0]} to {chain[-1]}"
            )
            valid_chains.append(chain)

        if valid_chains:
            best_chain = max(valid_chains, key=lambda c: evaluate_chain_smart(c))
            chain_score = evaluate_chain_smart(best_chain)
            print(
                f"[BEST] length={length} score={chain_score:.1f} "
                f"chain={best_chain}"
            )

            # быстрая остановка
            if chain_score > 100 or length <= 5:
                return best_chain

    # 4) запасной проход по всем цепочкам, если выше ничего не вернулось
    all_valid_chains: list[list[tuple[int, int]]] = []
    for chain in chains:
        move_key = (
            f"chain_{len(chain)}_{chain[0][0]}_{chain[0][1]}_"
            f"{chain[-1][0]}_{chain[-1][1]}"
        )
        if is_move_blacklisted(board_hash, move_key):
            continue

        score = evaluate_chain_smart(chain)
        print(
            f"[EVAL-FB] len={len(chain)} score={score:.1f} "
            f"from {chain[0]} to {chain[-1]}"
        )
        all_valid_chains.append(chain)

    if all_valid_chains:
        best_chain = max(all_valid_chains, key=lambda c: evaluate_chain_smart(c))
        chain_score = evaluate_chain_smart(best_chain)
        print(f"[BEST-FB] score={chain_score:.1f} chain={best_chain}")
        return best_chain

    print("[FBC] return None")
    return None
