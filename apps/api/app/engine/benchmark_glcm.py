import time
import numpy as np
from skimage.feature import graycomatrix, graycoprops

def benchmark_glcm_runtime(tile_size: int = 48, n_tiles: int = 500) -> float:
    """
    Benchmarks GLCM texture extraction across random crop tiles.
    Uses 16 gray levels, distances {1, 3}, 4 angles {0, 45, 90, 135}.
    """
    dummy_tiles = [
        np.random.randint(0, 16, (tile_size, tile_size), dtype=np.uint8)
        for _ in range(n_tiles)
    ]
    
    start = time.perf_counter()
    for tile in dummy_tiles:
        glcm = graycomatrix(
            tile,
            distances=[1, 3],
            angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
            levels=16,
            symmetric=True,
            normed=True
        )
        contrast = graycoprops(glcm, 'contrast')
        homogeneity = graycoprops(glcm, 'homogeneity')
        energy = graycoprops(glcm, 'energy')

    elapsed = time.perf_counter() - start
    return elapsed

if __name__ == "__main__":
    t = benchmark_glcm_runtime(tile_size=48, n_tiles=500)
    print(f"GLCM 500 tiles benchmark: {t:.3f}s (estimated {(t * 10):.2f}s for full 5000 tiles)")

