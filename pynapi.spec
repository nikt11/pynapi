Summary:	pynapi - Movie Subtitle Downloader
Name:		pynapi
Version:	0.2
Release:	1
License:	GPL
Group:		Applications/Multimedia
Source0:	pynapi.py
# Source0-md5:	558c3620ec8730b1476e7ebe2d9f6802
BuildRequires:	python-modules
Requires:	p7zip
%pyrequires_eq  python-modules
BuildArch:	noarch
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
Command line NAPI-PROJEKT subtitles downloader.

%prep
%setup -q -c -T

%build

%install
rm -rf $RPM_BUILD_ROOT

install -d $RPM_BUILD_ROOT%{_bindir}

install %{SOURCE0} $RPM_BUILD_ROOT%{_bindir}/pynapi

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(644,root,root,755)
%attr(755,root,root) %{_bindir}/pynapi