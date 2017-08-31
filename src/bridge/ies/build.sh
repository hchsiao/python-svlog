INCLUDE_PATH1=/opt/Cadence/INCISIV/cur/tools/include
PY_CFG=python-config

cd src
gcc -fPIC -shared -o invoke.so invoke.c -I$INCLUDE_PATH1 `$PY_CFG --cflags` `$PY_CFG --ldflags`
mv invoke.so ../test/lib
cd ..

cp ./src/*.py ./test/lib
mv ./test/lib/gen.py ./test/cache
cp -R ./src/tmpl ./test/cache

cd test
python cache/gen.py
cd ..

