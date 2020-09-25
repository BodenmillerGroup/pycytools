
build_dist:
	python setup.py sdist bdist_wheel

upload_test: build_dist
	python -m twine upload --repository testpypi dist/*

upload_pypi: build_dist
	python -m twine upload dist/*

./condabuild:
	mkdir condabuild

./condabuild/pycytools/meta.yaml: ./condabuild, upload_pypi
	cd condabuild;\
		conda skeleton pypi pycytools

conda_build: ./condabuild/pycytools/meta.yaml
	cd condabuild;\
	mamba build pycytools



