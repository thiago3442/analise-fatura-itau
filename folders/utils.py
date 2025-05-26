import re
import numpy as np

def limpar_valor(valor):
    """Cleans currency strings and converts to float."""
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str): # Corrected 'is str' to 'isinstance(valor, str)'
        # Remove currency symbols, spaces, and replace comma decimal separator
        valor_limpo = re.sub(r'[R$\s]', '', valor).replace(',', '.')
        try:
            return float(valor_limpo)
        except ValueError:
            # Handle cases where comma might be used as thousands separator
            valor_limpo_alt = valor.replace('.', '').replace(',', '.')
            try:
                return float(valor_limpo_alt)
            except ValueError:
                return np.nan # Return NaN if conversion fails
    return np.nan # Return NaN for other types
