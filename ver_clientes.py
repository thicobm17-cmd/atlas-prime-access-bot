from database import list_clientes

clientes = list_clientes()

for c in clientes:
    print(dict(c))