"""Game 的测试：性质断言 + 与参考实现的最小交叉验证。

Game 的雷位由 rng.sample 决定，测试无法指定布局。
因此本文件只做"性质断言 + 与参考实现的最小交叉验证"；
精确布局的用例只存在于 tests/test_reference.py。
"""
import pytest

from minesweeper.core import Game, GameState
from tests.reference import RefBoard


# ========== 构造与校验 ==========

def test_game_9x9_72_ok():
    g = Game(9, 9, 72)
    assert g.rows == 9 and g.cols == 9 and g.mines == 72


def test_game_9x9_73_raises():
    with pytest.raises(ValueError) as exc:
        Game(9, 9, 73)
    msg = str(exc.value)
    assert "72" in msg and "73" in msg


def test_game_2x2_0_ok():
    Game(2, 2, 0)


def test_game_2x2_1_raises():
    with pytest.raises(ValueError):
        Game(2, 2, 1)


def test_game_3x3_0_ok():
    Game(3, 3, 0)


def test_game_3x3_1_raises():
    with pytest.raises(ValueError):
        Game(3, 3, 1)


def test_game_zero_dim_raises():
    with pytest.raises(ValueError):
        Game(0, 5, 0)
    with pytest.raises(ValueError):
        Game(5, 0, 0)


def test_game_negative_mines_raises():
    with pytest.raises(ValueError):
        Game(3, 3, -1)


# ========== 首点安全（A2）==========

def test_first_click_safety_10000_games():
    """9×9 / 10 雷，三类位置各约 1/3，共 10000 次。"""
    import random
    rng = random.Random(42)
    corners = [(0, 0), (0, 8), (8, 0), (8, 8)]
    edges = [(0, 4), (4, 0), (4, 8), (8, 4)]
    internals = [(4, 4), (3, 3), (5, 5)]

    for _ in range(10000):
        choice = rng.randint(0, 2)
        if choice == 0:
            r, c = rng.choice(corners)
        elif choice == 1:
            r, c = rng.choice(edges)
        else:
            r, c = rng.choice(internals)

        g = Game(9, 9, 10, seed=rng.randint(0, 2**31))
        delta = g.reveal(r, c)
        assert g.state is not GameState.LOST
        assert g.view(r, c).revealed is True
        assert g.view(r, c).mine is False
        protected = {(r, c)}
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < 9 and 0 <= nc < 9:
                    protected.add((nr, nc))
        mines = g.snapshot_mines()
        for cell in protected:
            assert cell not in mines


# ========== 布雷与展开的性质 ==========

def test_mine_count_after_first_reveal():
    g = Game(9, 9, 10, seed=1)
    g.reveal(4, 4)
    assert g._board.mine_count == 10


def test_first_click_in_delta():
    g = Game(9, 9, 10, seed=2)
    delta = g.reveal(4, 4)
    assert (4, 4) in delta
    assert len(delta) >= 1


def test_delta_no_mines_when_first_click_safe():
    g = Game(9, 9, 10, seed=3)
    delta = g.reveal(4, 4)
    if g.state is not GameState.LOST:
        mines = g.snapshot_mines()
        assert all(cell not in mines for cell in delta)


def test_expansion_structure():
    """除首点外，delta 中每个 adjacent > 0 的格，至少有一个 adjacent == 0 的已翻开邻居。"""
    g = Game(9, 9, 10, seed=4)
    delta = g.reveal(4, 4)
    if g.state is GameState.LOST:
        return
    delta_set = set(delta)
    for r, c in delta:
        if (r, c) == (4, 4):
            continue
        adj = g._board.adjacent_at(r, c)
        if adj > 0:
            has_zero_neighbor = False
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if (nr, nc) in delta_set and g._board.adjacent_at(nr, nc) == 0:
                        has_zero_neighbor = True
                        break
                if has_zero_neighbor:
                    break
            assert has_zero_neighbor, f"格 ({r},{c}) adjacent={adj} 但无 0 邻居"


def test_revealed_cell_adjacent_matches_board():
    g = Game(9, 9, 10, seed=5)
    g.reveal(4, 4)
    for r, c in g.revealed_cells:
        assert g.view(r, c).adjacent == g._board.adjacent_at(r, c)


# ========== 重复操作 ==========

def test_same_cell_twice():
    g = Game(9, 9, 10, seed=6)
    delta1 = g.reveal(4, 4)
    before = g.revealed_cells
    delta2 = g.reveal(4, 4)
    assert delta2 == []
    assert g.revealed_cells == before


def test_two_deltas_disjoint():
    """先点零格、再点另一非零格：两次 delta 交集为空。"""
    g = Game(9, 9, 10, seed=7)
    delta1 = g.reveal(0, 0)
    if g.state is GameState.LOST:
        return
    for r in range(9):
        for c in range(9):
            if (r, c) not in g.revealed_cells and g._board.adjacent_at(r, c) != 0:
                delta2 = g.reveal(r, c)
                assert set(delta1).isdisjoint(set(delta2))
                return


# ========== 胜负（全部确定性，不依赖 seed）==========

def test_9x9_72_reveal_center_wins():
    """Game(9,9,72) + reveal(4,4) → delta 恰 9 格，state is WON。"""
    g = Game(9, 9, 72)
    delta = g.reveal(4, 4)
    assert len(delta) == 9
    assert g.state is GameState.WON


def test_2x2_0_reveal_wins():
    g = Game(2, 2, 0)
    delta = g.reveal(0, 0)
    assert len(delta) == 4
    assert g.state is GameState.WON


def test_1x3_0_reveal_wins():
    g = Game(1, 3, 0)
    delta = g.reveal(0, 1)
    assert len(delta) == 3
    assert g.state is GameState.WON


def test_step_on_mine_loses():
    """踩雷：先 reveal 一个安全格，再从 snapshot_mines 取一个雷格 reveal 它。"""
    g = Game(9, 9, 10, seed=8)
    g.reveal(4, 4)
    if g.state is GameState.LOST:
        return
    mines = g.snapshot_mines()
    mine_cell = next(iter(mines))
    before_count = len(g.revealed_cells)
    delta = g.reveal(mine_cell[0], mine_cell[1])
    assert g.state is GameState.LOST
    assert g.exploded_cell == mine_cell
    assert delta == [mine_cell]
    assert len(g.revealed_cells) == before_count + 1


def test_reveal_after_lost_returns_empty():
    g = Game(9, 9, 10, seed=9)
    g.reveal(4, 4)
    if g.state is not GameState.LOST:
        mines = g.snapshot_mines()
        mine_cell = next(iter(mines))
        g.reveal(mine_cell[0], mine_cell[1])
    assert g.state is GameState.LOST
    for r in range(9):
        for c in range(9):
            if (r, c) not in g.revealed_cells:
                assert g.reveal(r, c) == []
                return


# ========== 与参考实现的最小交叉验证（20 局）==========

def test_cross_check_first_click_20_games():
    for seed in range(20):
        g = Game(9, 9, 10, seed=seed)
        delta = g.reveal(4, 4)
        layout = g.snapshot_mines()
        ref = RefBoard(9, 9, layout)
        ref.expand(4, 4)
        assert set(g.revealed_cells) == set(ref.revealed_numbers())
        assert set(delta) == set(g.revealed_cells)


# ========== 信息不泄露（A6 的信息面）==========

def test_no_mine_info_during_playing():
    """布雷后、PLAYING 时：全部格 view().mine 为 False。"""
    g = Game(9, 9, 10, seed=10)
    g.reveal(4, 4)
    if g.state is GameState.LOST:
        return
    for r in range(9):
        for c in range(9):
            assert g.view(r, c).mine is False


def test_no_info_before_reveal():
    """reveal 之前：全部格 revealed is False / adjacent == 0 / mine is False。"""
    g = Game(9, 9, 10, seed=11)
    for r in range(9):
        for c in range(9):
            v = g.view(r, c)
            assert v.revealed is False
            assert v.adjacent == 0
            assert v.mine is False
    assert g.revealed_cells == frozenset()


def test_mine_info_after_lost():
    """LOST 后：所有雷格 mine is True，非雷格 mine is False。"""
    g = Game(9, 9, 10, seed=12)
    g.reveal(4, 4)
    if g.state is not GameState.LOST:
        mines = g.snapshot_mines()
        mine_cell = next(iter(mines))
        g.reveal(mine_cell[0], mine_cell[1])
    assert g.state is GameState.LOST
    mines = g.snapshot_mines()
    for r in range(9):
        for c in range(9):
            v = g.view(r, c)
            if (r, c) in mines:
                assert v.mine is True
            else:
                assert v.mine is False


def test_snapshot_mines_before_reveal_raises():
    """snapshot_mines() 在布雷前调用 → RuntimeError。"""
    g = Game(9, 9, 10, seed=13)
    with pytest.raises(RuntimeError):
        g.snapshot_mines()


# ========== 异常 ==========

def test_reveal_out_of_bounds():
    g = Game(9, 9, 10, seed=14)
    with pytest.raises(IndexError):
        g.reveal(-1, 0)
    with pytest.raises(IndexError):
        g.reveal(9, 0)


def test_view_out_of_bounds():
    g = Game(9, 9, 10, seed=15)
    with pytest.raises(IndexError):
        g.view(0, 9)


def test_reveal_out_of_bounds_after_lost():
    """LOST 后 reveal(-1,0) 仍抛 IndexError（D10）。"""
    g = Game(9, 9, 10, seed=16)
    g.reveal(4, 4)
    if g.state is not GameState.LOST:
        mines = g.snapshot_mines()
        mine_cell = next(iter(mines))
        g.reveal(mine_cell[0], mine_cell[1])
    assert g.state is GameState.LOST
    with pytest.raises(IndexError):
        g.reveal(-1, 0)


# ========== 插旗基础（T4 §5）==========

def test_flag_before_mines_placed():
    """未布雷即可插旗：toggle_flag 返回 [(r,c)]，view.flagged True，mines_left 减 1。"""
    g = Game(9, 9, 10)
    assert g.toggle_flag(0, 0) == [(0, 0)]
    assert g.view(0, 0).flagged is True
    assert g.mines_left == 9


def test_flag_toggle_off():
    """再次调用撤旗：返回 [(r,c)]，flagged False，mines_left 恢复。"""
    g = Game(9, 9, 10)
    g.toggle_flag(0, 0)
    assert g.toggle_flag(0, 0) == [(0, 0)]
    assert g.view(0, 0).flagged is False
    assert g.mines_left == 10


def test_flag_on_revealed_cell_returns_empty():
    """已翻开格不可插旗：toggle_flag 返回 []，flagged 仍 False。"""
    g = Game(9, 9, 10, seed=20)
    g.reveal(4, 4)
    assert g.view(4, 4).revealed is True
    assert g.toggle_flag(4, 4) == []
    assert g.view(4, 4).flagged is False


def test_flag_count_exceeds_mines():
    """旗数超雷数：不抛异常，mines_left 可为负（D13）。"""
    g = Game(9, 9, 1)
    for r in range(5):
        g.toggle_flag(r, 0)
    assert g.mines_left == -4


def test_flag_out_of_bounds_raises():
    """越界 -> IndexError。"""
    g = Game(9, 9, 10)
    with pytest.raises(IndexError):
        g.toggle_flag(-1, 0)
    with pytest.raises(IndexError):
        g.toggle_flag(0, 9)


def test_flag_after_lost_returns_empty():
    """LOST 后 toggle_flag -> []。"""
    g = Game(9, 9, 10, seed=21)
    g.reveal(4, 4)
    if g.state is not GameState.LOST:
        mines = g.snapshot_mines()
        mine_cell = next(iter(mines))
        g.reveal(mine_cell[0], mine_cell[1])
    assert g.state is GameState.LOST
    assert g.toggle_flag(0, 0) == []


# ========== D9 与 D16 组合（确定性）==========

def test_d9_d16_flag_blocks_flood_then_win():
    """Game(9,9,0)：插旗 (4,4) 后 reveal(0,0) -> 80 格、(4,4) 未翻开、PLAYING。
    撤旗后 reveal(4,4) -> 81 格、WON。"""
    g = Game(9, 9, 0)
    g.toggle_flag(4, 4)
    g.reveal(0, 0)
    assert len(g.revealed_cells) == 80
    assert (4, 4) not in g.revealed_cells
    assert g.state is GameState.PLAYING

    g.toggle_flag(4, 4)
    g.reveal(4, 4)
    assert len(g.revealed_cells) == 81
    assert g.state is GameState.WON


# ========== chord ==========

def test_chord_on_unrevealed_returns_empty():
    """未翻开格 chord -> []。"""
    g = Game(9, 9, 10, seed=30)
    g.reveal(4, 4)
    # 找一个未翻开的格
    for r in range(9):
        for c in range(9):
            if (r, c) not in g.revealed_cells:
                assert g.chord(r, c) == []
                return


def test_chord_on_zero_cell_returns_empty():
    """已翻开且 adjacent==0 的格 chord -> []。"""
    g = Game(9, 9, 10, seed=31)
    g.reveal(4, 4)
    # 找一个已翻开且 adjacent==0 的格
    for (r, c) in g.revealed_cells:
        if g.view(r, c).adjacent == 0:
            assert g.chord(r, c) == []
            return


def test_chord_flag_mismatch_is_atomic():
    """旗数不匹配时 chord -> []，且 _revealed/_flagged/_state 均不变。
    用 snapshot_mines() 动态寻找 adjacent >= 2 的已翻开格，不写死坐标。"""
    g = Game(9, 9, 10, seed=32)
    g.reveal(4, 4)
    mines = g.snapshot_mines()

    # 动态搜索 adjacent >= 2 的已翻开格
    target = None
    for (r, c) in g.revealed_cells:
        if g.view(r, c).adjacent >= 2:
            target = (r, c)
            break
    assert target is not None, "盘面中应存在 adjacent >= 2 的已翻开格"

    # 在 target 的雷邻居中只插 1 面旗（制造 mismatch）
    tr, tc = target
    mine_neighbors = [
        (tr + dr, tc + dc)
        for dr in (-1, 0, 1) for dc in (-1, 0, 1)
        if (dr, dc) != (0, 0)
        and g._in_bounds(tr + dr, tc + dc)
        and (tr + dr, tc + dc) in mines
    ]
    assert len(mine_neighbors) >= 2
    g.toggle_flag(*mine_neighbors[0])

    # 记录调用前快照
    prev_revealed = set(g.revealed_cells)
    prev_flagged = set(g._flagged)
    prev_state = g.state

    delta = g.chord(*target)
    assert delta == []
    assert set(g.revealed_cells) == prev_revealed
    assert set(g._flagged) == prev_flagged
    assert g.state is prev_state


def test_chord_correct_flags_reveals_neighbors():
    """正确插旗后 chord：返回集合恰好等于"未翻开、未插旗、非雷"的邻居。"""
    g = Game(9, 9, 10, seed=33)
    g.reveal(4, 4)
    mines = g.snapshot_mines()

    # 找一个有雷邻居的已翻开格
    target = None
    for (r, c) in g.revealed_cells:
        adj = g.view(r, c).adjacent
        if adj > 0:
            target = (r, c)
            break
    assert target is not None

    tr, tc = target
    # 把该格的所有雷邻居都插旗
    mine_neighbors = [
        (tr + dr, tc + dc)
        for dr in (-1, 0, 1) for dc in (-1, 0, 1)
        if (dr, dc) != (0, 0)
        and g._in_bounds(tr + dr, tc + dc)
        and (tr + dr, tc + dc) in mines
    ]
    for mn in mine_neighbors:
        g.toggle_flag(*mn)

    # 计算期望的返回集合：未翻开、未插旗、非雷的邻居
    expected = set()
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if (dr, dc) == (0, 0):
                continue
            nr, nc = tr + dr, tc + dc
            if not g._in_bounds(nr, nc):
                continue
            if (nr, nc) not in g.revealed_cells and (nr, nc) not in g._flagged and (nr, nc) not in mines:
                expected.add((nr, nc))

    delta = g.chord(*target)
    assert set(delta) == expected


def test_chord_wrong_flag_hits_mine():
    """adjacent==1 的格，旗插在非雷邻居上（数匹配但位置错）-> chord 踩雷。"""
    g = Game(9, 9, 10, seed=34)
    g.reveal(4, 4)
    mines = g.snapshot_mines()

    # 找一个 adjacent == 1 的已翻开格
    target = None
    for (r, c) in g.revealed_cells:
        if g.view(r, c).adjacent == 1:
            target = (r, c)
            break
    assert target is not None

    tr, tc = target
    # 找出该格的雷邻居和非雷邻居
    mine_neighbors = []
    safe_neighbors = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if (dr, dc) == (0, 0):
                continue
            nr, nc = tr + dr, tc + dc
            if not g._in_bounds(nr, nc):
                continue
            if (nr, nc) in mines:
                mine_neighbors.append((nr, nc))
            elif (nr, nc) not in g.revealed_cells:
                safe_neighbors.append((nr, nc))

    assert len(mine_neighbors) == 1
    assert len(safe_neighbors) >= 1

    # 把旗插在一个非雷邻居上（数匹配：adjacent==1, nf==1，但位置错）
    g.toggle_flag(*safe_neighbors[0])

    delta = g.chord(*target)
    assert g.state is GameState.LOST
    assert g.exploded_cell == mine_neighbors[0]
    assert mine_neighbors[0] in delta


def test_chord_delta_has_no_duplicates():
    """正确 chord 后断言 delta 无重复格。"""
    g = Game(9, 9, 10, seed=35)
    g.reveal(4, 4)
    mines = g.snapshot_mines()

    # 找一个有雷邻居的已翻开格并正确插旗
    target = None
    for (r, c) in g.revealed_cells:
        if g.view(r, c).adjacent > 0:
            target = (r, c)
            break
    assert target is not None

    tr, tc = target
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if (dr, dc) == (0, 0):
                continue
            nr, nc = tr + dr, tc + dc
            if g._in_bounds(nr, nc) and (nr, nc) in mines:
                g.toggle_flag(nr, nc)

    delta = g.chord(*target)
    assert len(delta) == len(set(delta))


# ========== 信息面 ==========

def test_flag_does_not_leak_mine_info():
    """插旗不泄露雷位：任意时刻对所有格断言 view(r,c).mine is False（非 LOST 时）。"""
    g = Game(9, 9, 10, seed=40)
    g.reveal(4, 4)
    if g.state is GameState.LOST:
        return
    # 插几面旗
    g.toggle_flag(0, 0)
    g.toggle_flag(0, 1)
    g.toggle_flag(0, 2)
    # 断言不泄露
    for r in range(9):
        for c in range(9):
            assert g.view(r, c).mine is False
