/home/op/ansible_toolkit/

uloc.txt		-- SN	ULOC
spp_check.py		-- checks files created by both SPP runs; depends /etc/ansible/hosts and /data/sfng/ipmapping
ipmapping_spp.py	-- new ipmapping with ssp chose options;  depends on uloc.txt
ipmapping_no_spp.py	-- old ipmapping without spp options; depends on uloc.txt
fw_check.py		-- fw check for most spp; depends on /etc/ansible/hosts and /data/sfng/ipmapping; generates FW_full.txt
