from repair_shop.world import JOBS, World
import pytest

@pytest.mark.parametrize('job',JOBS)
def test_all_jobs_discoverable_below_cap(job):
    w=World(job); steps=1; readings=w.call('inspect',{})
    assert 'recipe' not in readings
    if job.cooler:
        for op in w.recipe:
            if op not in readings['visible_progress']:
                assert w.call('operate',{'operation':op})['ok']; steps+=1
    if job.cable: w.call('operate',{'operation':'reseat_cable'}); steps+=1
    if job.fuse: w.call('operate',{'operation':'replace_fuse'}); steps+=1
    assert w.call('test',{})['pass']; steps+=1
    assert steps<=12

def test_wrong_order_and_invalid_are_no_ops():
    w=World(JOBS[0]); before=w.snapshot()
    assert not w.call('operate',{'operation':'tune'})['ok']
    assert before==w.snapshot()
    assert not w.call('operate',{'operation':'explode'})['ok']
    assert not w.passed

def test_instances_and_revisions_are_independent():
    a,b=World(JOBS[0]),World(JOBS[0])
    a.call('operate',{'operation':'vent'})
    assert b.progress==[]
    assert World(JOBS[8]).recipe!=b.recipe
