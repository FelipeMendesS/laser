# -*- coding: cp1252 -*-
import os
import zipfile

# colocar aqui o diretório do arquivo usando barra dupla (\\)
path = 'C:\\Users\\Usuário\\Desktop\\ITA\\ELE\\4º Semestre\\Projeto EEA-47\\Leitura_Arquivos'
path2 = 'C:\\Users\\Usuário\\Desktop'
os.chdir(path)

# lê o nome e a extebsão do arquivo
name = raw_input("Digite o nome do arquivo que deseja enviar: ")
ext = raw_input("Digite a extensão do arquivo: ")
arq = name + "." + ext

# cria um zip e adiciona o arquivo
zf = zipfile.ZipFile(name + ".zip", 'w')
zf.write(arq)
zf.close()

# lê o arquivo zipado como binário
with open(name + ".zip",'rb') as f:
    data = f.read()
os.remove(name + ".zip")

data_byte = bytearray(data)
N = len(data_byte)


# simulando a recepção
recebido_byte = bytearray(N)
for i in range(0,N):
    recebido_byte[i] = data_byte[i]

recebido = str(recebido_byte)

with open(name + "_saida.zip",'wb') as g:
    g.write(recebido)

zfile = zipfile.ZipFile(name + "_saida.zip")
zfile.extract(arq, path2)
zfile.close()
os.remove(name + "_saida.zip")
