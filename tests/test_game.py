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
