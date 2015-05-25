import mock
import pytest

import librarian.core.archive as mod


MOD = mod.__name__


@pytest.fixture
def mocked_backend():
    backend = mock.MagicMock(spec=mod.BaseArchive)
    init_flag = '_{0}__initialized'.format(mod.BaseArchive.__name__)
    setattr(backend, init_flag, True)
    return backend


class TestArchive(object):

    def test_init_invalid_backend(self):
        with pytest.raises(TypeError):
            mod.Archive(mock.MagicMock())

    def test_init_uninitialized_backend(self):
        with pytest.raises(RuntimeError):
            mod.Archive(mock.MagicMock(spec=mod.BaseArchive))

    def test_init_success(self, mocked_backend):
        archive = mod.Archive(mocked_backend)
        assert object.__getattribute__(archive, 'backend') is mocked_backend

    def test_archive_attr_access(self, mocked_backend):
        some_func = mock.Mock()
        mocked_backend.some_func = some_func
        archive = mod.Archive(mocked_backend)
        archive.some_func('param')
        some_func.assert_called_once_with('param')

    def test_archive_attr_set(self, mocked_backend):
        archive = mod.Archive(mocked_backend)

        with pytest.raises(AttributeError):
            object.__getattribute__(archive, 'test_attr')
        with pytest.raises(AttributeError):
            object.__getattribute__(mocked_backend, 'test_attr')

        archive.test_attr = 1

        with pytest.raises(AttributeError):
            object.__getattribute__(archive, 'test_attr')

        object.__getattribute__(mocked_backend, 'test_attr')

    @mock.patch('__builtin__.__import__')
    def test_get_backend_class_on_pythonpath(self, import_func):
        import_func.side_effect = mock.Mock()
        mod.Archive.get_backend_class('path.to.package.module.ClassName')
        import_func.assert_called_once_with('path.to.package.module.ClassName',
                                            fromlist=['ClassName'])

    def test_get_backend_class_not_on_pythonpath(self):
        original_import = __import__

        def mocked_import(package, *args, **kwargs):
            if package == 'localpkg.mod.ClassName':
                raise ImportError()

            if 'fromlist' not in kwargs:
                return original_import(package, *args, **kwargs)

            assert package == 'librarian.core.backends.localpkg.mod'
            assert kwargs['fromlist'] == ['ClassName']
            return mock.Mock(ClassName='backend_cls')

        with mock.patch('__builtin__.__import__') as import_func:
            import_func.side_effect = mocked_import
            cls = mod.Archive.get_backend_class('localpkg.mod.ClassName')
            assert cls == 'backend_cls'

    @mock.patch.object(mod.Archive, '__init__')
    @mock.patch.object(mod.Archive, 'get_backend_class')
    def test_setup(self, get_backend_class, init_func):
        mocked_backend = mock.Mock()
        mocked_backend_cls = mock.Mock()
        mocked_backend_cls.return_value = mocked_backend
        get_backend_class.return_value = mocked_backend_cls
        init_func.return_value = None

        mod.Archive.setup('backend_path', 1, 2, kw3=3, kw4=4)

        get_backend_class.assert_called_once_with('backend_path')
        mocked_backend_cls.assert_called_once_with(1, 2, kw3=3, kw4=4)
        init_func.assert_called_once_with(mocked_backend)


@pytest.fixture
def base_archive():
    return mod.BaseArchive(contentdir='unimportant',
                           spooldir='unimportant',
                           meta_filename='unimportant')


class TestBaseArchive(object):

    def test_base_archive_db_fields(self, base_archive):
        assert base_archive.db_fields == (
            'md5',
            'size',
            'updated',
            'publisher',
            'keep_formatting',
            'language',
            'license',
            'title',
            'url',
            'timestamp',
            'multipage',
            'broadcast',
            'keywords',
            'entry_point',
            'images',
            'is_partner',
            'is_sponsored',
            'archive'
        )

    def test_base_archive_init_fail(self):
        with pytest.raises(TypeError):
            mod.BaseArchive()

    def test_base_archive_init_success(self):
        archive = mod.BaseArchive(contentdir='test',
                                  spooldir='test',
                                  meta_filename='test')
        init_flag = '_{0}__initialized'.format(mod.BaseArchive.__name__)
        assert hasattr(archive, init_flag)

    @mock.patch.object(mod.BaseArchive, 'get_multiple')
    def test_add_repacement_data(self, get_multiple, base_archive):
        get_multiple.return_value = [{'md5': '123', 'title': 'old_content'}]
        metas = [
            {'md5': '456', 'title': 'first', 'replaces': '123'},
            {'md5': 'abc', 'title': 'second'}
        ]
        base_archive.add_replacement_data(metas, needed_keys=('title',))
        assert metas == [{'md5': '456',
                          'title': 'first',
                          'replaces': '123',
                          'replaces_title': 'old_content'},
                         {'md5': 'abc', 'title': 'second'}]
        get_multiple.assert_called_once_with(['123'], fields=('title',))

    @mock.patch.object(mod.BaseArchive, 'get_multiple')
    def test_add_repacement_data_no_match(self, get_multiple, base_archive):
        get_multiple.return_value = []
        metas = [{'md5': 'abc', 'title': 'second'}]
        base_archive.add_replacement_data(metas, needed_keys=('title',))
        assert metas == [{'md5': 'abc', 'title': 'second'}]
        assert not get_multiple.called

    @mock.patch.object(mod.content, 'to_path')
    @mock.patch.object(mod, 'shutil')
    def test_delete_content_files_success(self, shutil, to_path, base_archive):
        to_path.return_value = '/content_root/some_id/'
        assert base_archive.delete_content_files('some_id')
        shutil.rmtree.assert_called_once_with('/content_root/some_id/')

    @mock.patch.object(mod.content, 'to_path')
    @mock.patch.object(mod, 'shutil')
    def test_delete_content_files_invalid_content_id(self, shutil, to_path,
                                                     base_archive):
        to_path.return_value = None
        assert not base_archive.delete_content_files('some_id')
        assert not shutil.rmtree.called

    @mock.patch.object(mod.content, 'to_path')
    @mock.patch.object(mod, 'shutil')
    def test_delete_content_files_fail(self, shutil, to_path, base_archive):
        to_path.return_value = '/content_root/some_id/'
        shutil.rmtree.side_effect = OSError()
        assert not base_archive.delete_content_files('some_id')
        shutil.rmtree.assert_called_once_with('/content_root/some_id/')

    @mock.patch.object(mod.BaseArchive, 'delete_content_files')
    @mock.patch.object(mod.BaseArchive, 'add_meta_to_db')
    @mock.patch.object(mod.content, 'get_content_size')
    @mock.patch.object(mod.zipballs, 'extract')
    def test_process_content_success(self, extract, get_content_size,
                                     add_meta_to_db, delete_content_files,
                                     base_archive):
        content_id = 'some_id'
        meta = {'title': 'some title'}
        zip_path = '/path/file.zip'
        contentdir = base_archive.config['contentdir']

        def mocked_add_meta(meta):
            for key in ('title', 'md5', 'updated', 'size'):
                assert key in meta

            return 1

        add_meta_to_db.side_effect = mocked_add_meta
        assert base_archive.process_content(content_id, zip_path, meta) == 1
        extract.assert_called_once_with(zip_path, contentdir)
        get_content_size.assert_called_once_with(contentdir, content_id)
        assert add_meta_to_db.call_count == 1
        assert not delete_content_files.called

    @mock.patch.object(mod.BaseArchive, 'delete_content_files')
    @mock.patch.object(mod.BaseArchive, 'add_meta_to_db')
    @mock.patch.object(mod.zipballs, 'extract')
    def test_process_content_fail(self, extract, add_meta_to_db,
                                  delete_content_files, base_archive):
        extract.side_effect = IOError()
        assert base_archive.process_content('some_id', 'zip/path', {}) is False
        delete_content_files.assert_called_once_with('some_id')
        assert not add_meta_to_db.called

    @mock.patch.object(mod.BaseArchive, 'process_content')
    @mock.patch.object(mod.zipballs, 'validate')
    @mock.patch.object(mod.zipballs, 'get_zip_path')
    def test___add_to_archive_success(self, get_zip_path, validate,
                                      process_content, base_archive):
        content_id = 'some_id'
        get_zip_path.return_value = 'zipball path'
        process_content.return_value = 1
        validate.return_value = {'md5': content_id, 'title': 'test'}
        assert base_archive._BaseArchive__add_to_archive(content_id)
        get_zip_path.assert_called_once_with(content_id, 'unimportant')
        validate.assert_called_once_with('zipball path',
                                         meta_filename='unimportant')
        process_content.assert_called_once_with(content_id,
                                                get_zip_path.return_value,
                                                validate.return_value)

    @mock.patch.object(mod.BaseArchive, 'process_content')
    @mock.patch.object(mod.zipballs, 'validate')
    @mock.patch.object(mod.zipballs, 'get_zip_path')
    def test___add_to_archive_fail(self, get_zip_path, validate,
                                   process_content, base_archive):
        get_zip_path.return_value = 'zipball path'
        validate.side_effect = mod.zipballs.ValidationError('/path', 'msg')
        assert not base_archive._BaseArchive__add_to_archive('some_id')
        get_zip_path.assert_called_once_with('some_id', 'unimportant')
        validate.assert_called_once_with('zipball path',
                                         meta_filename='unimportant')
        assert not process_content.called

    @mock.patch.object(mod.BaseArchive, '_BaseArchive__add_to_archive')
    def test_add_to_archive(self, __add_to_archive, base_archive):
        __add_to_archive.return_value = 1
        assert base_archive.add_to_archive('some_id') == 1
        __add_to_archive.assert_called_once_with('some_id')

        assert base_archive.add_to_archive(['some_id', 'other_id']) == 2
        __add_to_archive.assert_has_calls([mock.call('some_id'),
                                           mock.call('other_id')])

    @mock.patch.object(mod.BaseArchive, 'remove_meta_from_db')
    @mock.patch.object(mod.BaseArchive, 'delete_content_files')
    def test___remove_from_archive(self, delete_content_files,
                                   remove_meta_from_db, base_archive):
        remove_meta_from_db.return_value = 1
        assert base_archive._BaseArchive__remove_from_archive('some_id')
        delete_content_files.assert_called_once_with('some_id')
        remove_meta_from_db.assert_called_once_with('some_id')

    @mock.patch.object(mod.BaseArchive, '_BaseArchive__remove_from_archive')
    def test_remove_from_archive(self, __remove_from_archive, base_archive):
        __remove_from_archive.return_value = 1
        assert base_archive.remove_from_archive('some_id') == 1
        __remove_from_archive.assert_called_once_with('some_id')

        assert base_archive.remove_from_archive(['some_id', 'other_id']) == 2
        __remove_from_archive.assert_has_calls([mock.call('some_id'),
                                                mock.call('other_id')])

    @mock.patch.object(mod.BaseArchive, 'process_content')
    @mock.patch.object(mod.content, 'to_md5')
    @mock.patch.object(mod.content, 'find_content_dirs')
    def test_reload_content(self, find_content_dirs, to_md5, process_content,
                            base_archive):
        to_md5.side_effect = lambda x: x.strip('/')
        find_content_dirs.return_value = ['unimportant/contentid',
                                          'unimportant/otherid']
        process_content.return_value = 1
        assert base_archive.reload_content() == 2
        to_md5.assert_has_calls([mock.call('contentid'), mock.call('otherid')])
        process_content.assert_has_calls([mock.call('contentid'),
                                          mock.call('otherid')])
