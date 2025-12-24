def find_best_chain_smart(self, board_hash):
    chains = self.find_all_chains()

    if not chains:
        return None

    chains_by_length = {}
    for chain in chains:
        length = len(chain)
        if length not in chains_by_length:
            chains_by_length[length] = []
        chains_by_length[length].append(chain)

    optimal_lengths = [4, 5, 3, 6, 2, 7, 8, 9]

    for length in optimal_lengths:
        if length in chains_by_length:
            valid_chains = []
            for chain in chains_by_length[length]:
                move_key = (
                    f"chain_{len(chain)}_{chain[0][0]}_{chain[0][1]}_"
                    f"{chain[-1][0]}_{chain[-1][1]}"
                )
                if not self.is_move_blacklisted(board_hash, move_key):
                    # ⬇️ временный отладочный вывод
                    score = self.evaluate_chain_smart(chain)
                    print(
                        f"[EVAL] len={len(chain)} score={score:.1f} "
                        f"from {chain[0]} to {chain[-1]}"
                    )
                    valid_chains.append(chain)

            if valid_chains:
                best_chain = max(
                    valid_chains, key=lambda c: self.evaluate_chain_smart(c)
                )
                chain_score = self.evaluate_chain_smart(best_chain)
                print(
                    f"[BEST] length={length} score={chain_score:.1f} chain={best_chain}"
                )

                if chain_score > 100 or length <= 5:
                    return best_chain

    all_valid_chains = []
    for chain in chains:
        move_key = (
            f"chain_{len(chain)}_{chain[0][0]}_{chain[0][1]}_"
            f"{chain[-1][0]}_{chain[-1][1]}"
        )
        if not self.is_move_blacklisted(board_hash, move_key):
            score = self.evaluate_chain_smart(chain)
            print(
                f"[EVAL-FB] len={len(chain)} score={score:.1f} "
                f"from {chain[0]} to {chain[-1]}"
            )
            all_valid_chains.append(chain)

    if all_valid_chains:
        best_chain = max(all_valid_chains, key=lambda c: self.evaluate_chain_smart(c))
        chain_score = self.evaluate_chain_smart(best_chain)
        print(f"[BEST-FB] score={chain_score:.1f} chain={best_chain}")
        return best_chain

    return None
