source 'https://rubygems.org'

# You may use http://rbenv.org/ or https://rvm.io/ to install and use this version
ruby ">= 3.1.0"

# Exclude problematic versions of cocoapods that cause build failures.
gem 'cocoapods', '>= 1.13', '!= 1.15.0', '!= 1.15.1'
# activesupport < 7.2.3.1 has known security advisories.
gem 'activesupport', '>= 7.2.3.1', '< 8'
gem 'xcodeproj', '< 1.26.0'
# concurrent-ruby < 1.3.7 has known security advisories.
gem 'concurrent-ruby', '~> 1.3.7'

# Ruby 3.4.0 has removed some libraries from the standard library.
gem 'bigdecimal'
gem 'logger'
gem 'benchmark'
gem 'mutex_m'
gem 'nkf'
