from scipy import stats
from utils.read_samples import read_samples

x0 = read_samples(f"token-timing-224a{'0' * 36}.txt")
x1 = read_samples(f"token-timing-224c{'0' * 36}.txt")
x2 = read_samples('token-timing-224a93060c0dd4fb931d05083b4cb7b6a8c27df8.txt')

z_stat, p_val = stats.ranksums(x2, x0)

print(f'MWW RankSum P for input samples: {p_val}')
print(f'MWW RankSum Z for input samples: {z_stat}')
print('')
print('== 0.00  means totally different')
print('<= 0.05  highly confident that the distributions significantly differ')
