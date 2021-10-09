# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['D:\\_Capstone Project\\_Aplikasi\\GUI'],
             binaries=[],
             datas=[( 'model/mean_per_channel_train_fold_5.npy', 'model' ),
                    ( 'model/std_per_channel_train_fold_5.npy', 'model' ),
					( 'model/ResNet50_ReFold_5_40.h5', 'model' ),
					( 'resources/logo.png', 'resources' )],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Aplikasi Klasifikasi COVID-19',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Aplikasi Klasifikasi COVID-19')
