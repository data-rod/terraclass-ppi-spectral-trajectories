"""Native linear-algebra constraint for replaying the published MNF–PPI run."""
from threadpoolctl import threadpool_info
import numpy as np

def require_ppi_backend():
    backends=threadpool_info()
    compiled=np.show_config(mode='dicts').get('Build Dependencies',{})
    fixed_numpy=(np.__version__=='2.1.3' and all('mkl' in compiled.get(k,{}).get('name','').lower() and str(compiled.get(k,{}).get('version','')).startswith('2023.1') for k in ['blas','lapack']))
    if not fixed_numpy or not any(b.get('internal_api')=='mkl' and str(b.get('version','')).startswith('2023.1') for b in backends):
        raise RuntimeError('Full MNF–PPI replay requires NumPy 2.1.3 linked to Intel MKL 2023.1. Use environment-full-mkl.yml. Pip/OpenBLAS is supported for the verified model/STL reference routes, but does not reproduce the original MNF eigenvector frame.')
    return dict(numpy=np.__version__,compiled_blas=compiled['blas']['name'],compiled_lapack=compiled['lapack']['name'],runtime=[dict(api=b.get('internal_api'),version=b.get('version'),threads=b.get('num_threads')) for b in backends])
